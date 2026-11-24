"""SQLite local das auditorias.

Idempotência: `startup_requests.startup_id` é UNIQUE e o pedido é resolvido dentro de BEGIN IMMEDIATE.
Um índice único parcial impede dois jobs ativos do mesmo projeto/perfil (duplo clique simultâneo).
"""

from __future__ import annotations

import json
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ACTIVE = ("queued", "collecting")
TERMINAL = ("completed", "partial", "failed", "cancelled", "interrupted")
PRESENT = ("new", "recurring", "not_rechecked")  # ainda podem existir no projeto

SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_runs (
  id TEXT PRIMARY KEY, project TEXT NOT NULL, profile TEXT NOT NULL, trigger TEXT NOT NULL,
  state TEXT NOT NULL, created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT,
  summary TEXT, revision TEXT, error TEXT, sync_state TEXT NOT NULL DEFAULT 'local_only',
  checks_total INTEGER NOT NULL DEFAULT 0, checks_done INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_run ON audit_runs(project, profile)
  WHERE state IN ('queued', 'collecting');
CREATE INDEX IF NOT EXISTS runs_by_date ON audit_runs(created_at DESC, id DESC);
CREATE TABLE IF NOT EXISTS startup_requests (
  startup_id TEXT PRIMARY KEY, run_id TEXT REFERENCES audit_runs(id), trigger TEXT NOT NULL,
  outcome TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS check_results (
  run_id TEXT NOT NULL REFERENCES audit_runs(id), check_id TEXT NOT NULL, position INTEGER NOT NULL,
  name TEXT NOT NULL, status TEXT NOT NULL, note TEXT, duration_ms INTEGER, PRIMARY KEY (run_id, check_id)
);
CREATE TABLE IF NOT EXISTS findings (
  fingerprint TEXT PRIMARY KEY, rule TEXT NOT NULL, first_seen_run TEXT NOT NULL, first_seen_at TEXT NOT NULL,
  last_seen_run TEXT NOT NULL, last_seen_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS run_findings (
  run_id TEXT NOT NULL REFERENCES audit_runs(id), fingerprint TEXT NOT NULL, check_id TEXT NOT NULL,
  rule TEXT NOT NULL, severity TEXT NOT NULL, state TEXT NOT NULL, comparison TEXT NOT NULL,
  summary TEXT NOT NULL, file TEXT, line INTEGER, PRIMARY KEY (run_id, fingerprint)
);
CREATE TABLE IF NOT EXISTS artifacts (
  run_id TEXT NOT NULL REFERENCES audit_runs(id), kind TEXT NOT NULL, name TEXT NOT NULL,
  sha256 TEXT NOT NULL, bytes INTEGER NOT NULL, PRIMARY KEY (run_id, kind)
);
CREATE TABLE IF NOT EXISTS investigations (
  run_id TEXT PRIMARY KEY REFERENCES audit_runs(id), state TEXT NOT NULL, trigger TEXT NOT NULL,
  attempt INTEGER NOT NULL DEFAULT 1, provider TEXT, model TEXT, prompt_version TEXT, requested_at TEXT NOT NULL,
  started_at TEXT, finished_at TEXT, error TEXT, findings_total INTEGER NOT NULL DEFAULT 0,
  findings_done INTEGER NOT NULL DEFAULT 0, report_sha256 TEXT, result_sha256 TEXT
);
"""
INVESTIGATION_ACTIVE = ("queued", "running")


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")  # ordena runs do mesmo segundo


def new_run_id() -> str:
    return datetime.now(UTC).strftime("AUD-%Y%m%d-%H%M%S-") + secrets.token_hex(3)


class AuditStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.RLock()
        self._db = sqlite3.connect(path, check_same_thread=False, isolation_level=None, timeout=10)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.executescript(SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._db.close()

    @contextmanager
    def tx(self):
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                yield self._db
            except BaseException:
                self._db.execute("ROLLBACK")
                raise
            self._db.execute("COMMIT")

    def _one(self, sql: str, *args: Any) -> sqlite3.Row | None:
        with self._lock:
            return self._db.execute(sql, args).fetchone()

    def _all(self, sql: str, *args: Any) -> list[sqlite3.Row]:
        with self._lock:
            return self._db.execute(sql, args).fetchall()

    # Pedidos ---------------------------------------------------------------------------------

    def request(self, key: str, project: str, profile: str, trigger: str, checks_total: int) -> dict[str, Any]:
        """Resolve um pedido idempotente: repetido, agregado a um job ativo ou novo."""
        with self.tx() as db:
            seen = db.execute("SELECT run_id, outcome FROM startup_requests WHERE startup_id = ?", (key,)).fetchone()
            if seen is not None:
                return {"run_id": seen["run_id"], "outcome": seen["outcome"], "duplicate": True}
            active = db.execute("SELECT id FROM audit_runs WHERE project = ? AND profile = ? AND state IN (?, ?)",
                                (project, profile, *ACTIVE)).fetchone()
            if active is not None:
                db.execute("INSERT INTO startup_requests VALUES (?, ?, ?, 'coalesced', ?)",
                           (key, active["id"], trigger, now()))
                return {"run_id": active["id"], "outcome": "coalesced", "duplicate": False}
            run_id = new_run_id()
            db.execute("INSERT INTO audit_runs (id, project, profile, trigger, state, created_at, checks_total) "
                       "VALUES (?, ?, ?, ?, 'queued', ?, ?)", (run_id, project, profile, trigger, now(), checks_total))
            db.execute("INSERT INTO startup_requests VALUES (?, ?, ?, 'created', ?)", (key, run_id, trigger, now()))
            return {"run_id": run_id, "outcome": "created", "duplicate": False}

    def record_disabled(self, key: str, trigger: str) -> dict[str, Any]:
        with self.tx() as db:
            seen = db.execute("SELECT run_id, outcome FROM startup_requests WHERE startup_id = ?", (key,)).fetchone()
            if seen is not None:
                return {"run_id": seen["run_id"], "outcome": seen["outcome"], "duplicate": True}
            db.execute("INSERT INTO startup_requests VALUES (?, NULL, ?, 'disabled', ?)", (key, trigger, now()))
            return {"run_id": None, "outcome": "disabled", "duplicate": False}

    def last_startup(self) -> dict[str, Any] | None:
        row = self._one("SELECT * FROM startup_requests WHERE trigger = 'startup' ORDER BY created_at DESC LIMIT 1")
        return dict(row) if row else None

    # Ciclo de vida ---------------------------------------------------------------------------

    def recover(self) -> int:
        """No reinício, nada fica 'em andamento' sem processo: vira interrupted e não é reexecutado."""
        with self.tx() as db:
            return db.execute("UPDATE audit_runs SET state = 'interrupted', finished_at = ?, "
                              "error = 'O serviço foi encerrado durante a coleta; o job não foi reexecutado.' "
                              "WHERE state IN (?, ?)", (now(), *ACTIVE)).rowcount

    def next_queued(self) -> sqlite3.Row | None:
        return self._one("SELECT * FROM audit_runs WHERE state = 'queued' ORDER BY created_at, id LIMIT 1")

    def start(self, run_id: str) -> bool:
        with self.tx() as db:
            return db.execute("UPDATE audit_runs SET state = 'collecting', started_at = ? WHERE id = ? "
                              "AND state = 'queued'", (now(), run_id)).rowcount == 1

    def cancel_queued(self, run_id: str) -> bool:
        with self.tx() as db:
            return db.execute("UPDATE audit_runs SET state = 'cancelled', finished_at = ?, error = 'Cancelado antes "
                              "de iniciar.' WHERE id = ? AND state = 'queued'", (now(), run_id)).rowcount == 1

    def save_check(self, run_id: str, position: int, check: dict[str, Any]) -> None:
        with self.tx() as db:
            db.execute("INSERT OR REPLACE INTO check_results VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (run_id, check["id"], position, check["name"], check["status"], check["note"],
                        check.get("duration_ms")))
            db.execute("UPDATE audit_runs SET checks_done = (SELECT COUNT(*) FROM check_results WHERE run_id = ?) "
                       "WHERE id = ?", (run_id, run_id))

    def previous_findings(self, project: str, profile: str, run_id: str) -> tuple[str | None, list[sqlite3.Row]]:
        prev = self._one("SELECT id FROM audit_runs WHERE project = ? AND profile = ? AND id != ? "
                         "AND state IN ('completed', 'partial') ORDER BY created_at DESC, id DESC LIMIT 1",
                         project, profile, run_id)
        if prev is None:
            return None, []
        rows = self._all("SELECT * FROM run_findings WHERE run_id = ? AND comparison IN (?, ?, ?)",
                         prev["id"], *PRESENT)
        return prev["id"], rows

    def finalize(self, run_id: str, state: str, summary: dict[str, Any], revision: dict[str, Any],
                 findings: list[dict[str, Any]], artifacts: list[dict[str, Any]], finished_at: str) -> None:
        """Uma transação: run final, achados comparados e artefatos (nada fica pela metade)."""
        stamp = finished_at
        with self.tx() as db:
            for item in findings:
                db.execute("INSERT OR REPLACE INTO run_findings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (run_id, item["fingerprint"], item["check_id"], item["rule"], item["severity"],
                            item["state"], item["comparison"], item["summary"], item.get("file"), item.get("line")))
                if item["comparison"] in ("new", "recurring"):
                    db.execute("INSERT INTO findings VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(fingerprint) DO UPDATE "
                               "SET last_seen_run = excluded.last_seen_run, last_seen_at = excluded.last_seen_at",
                               (item["fingerprint"], item["rule"], run_id, stamp, run_id, stamp))
            for art in artifacts:
                db.execute("INSERT OR REPLACE INTO artifacts VALUES (?, ?, ?, ?, ?)",
                           (run_id, art["kind"], art["name"], art["sha256"], art["bytes"]))
            db.execute("UPDATE audit_runs SET state = ?, finished_at = ?, summary = ?, revision = ? WHERE id = ?",
                       (state, stamp, json.dumps(summary, ensure_ascii=False),
                        json.dumps(revision, ensure_ascii=False), run_id))

    def fail(self, run_id: str, state: str, error: str) -> None:
        with self.tx() as db:
            db.execute("UPDATE audit_runs SET state = ?, finished_at = ?, error = ? WHERE id = ?",
                       (state, now(), error, run_id))

    # Leitura ---------------------------------------------------------------------------------

    @staticmethod
    def _run(row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        data["summary"] = json.loads(data["summary"]) if data["summary"] else None
        data["revision"] = json.loads(data["revision"]) if data["revision"] else None
        return data

    def run(self, run_id: str) -> dict[str, Any] | None:
        row = self._one("SELECT * FROM audit_runs WHERE id = ?", run_id)
        if row is None:
            return None
        data = self._run(row)
        data["startup_ids"] = [r["startup_id"] for r in self._all(
            "SELECT startup_id FROM startup_requests WHERE run_id = ? ORDER BY created_at", run_id)]
        data["checks"] = [dict(r) for r in self._all(
            "SELECT check_id AS id, name, status, note, duration_ms FROM check_results WHERE run_id = ? "
            "ORDER BY position", run_id)]
        data["artifacts"] = [dict(r) for r in self._all("SELECT kind, name, sha256, bytes FROM artifacts "
                                                        "WHERE run_id = ?", run_id)]
        return data

    def artifact(self, run_id: str, kind: str) -> sqlite3.Row | None:
        return self._one("SELECT * FROM artifacts WHERE run_id = ? AND kind = ?", run_id, kind)

    def runs(self, limit: int = 20, cursor: str | None = None, state: str | None = None,
             severity: str | None = None) -> dict[str, Any]:
        where, args = [], []
        if cursor:
            created, _, run_id = cursor.partition("|")
            where.append("(created_at < ? OR (created_at = ? AND id < ?))")
            args += [created, created, run_id]
        if state:
            where.append("state = ?")
            args.append(state)
        if severity:
            where.append("EXISTS (SELECT 1 FROM run_findings f WHERE f.run_id = audit_runs.id AND f.severity = ? "
                         "AND f.comparison IN ('new', 'recurring'))")
            args.append(severity)
        sql = ("SELECT * FROM audit_runs" + (" WHERE " + " AND ".join(where) if where else "")
               + " ORDER BY created_at DESC, id DESC LIMIT ?")
        rows = self._all(sql, *args, limit + 1)
        items = [self._run(r) for r in rows[:limit]]
        more = len(rows) > limit
        return {"items": items, "next_cursor": f"{items[-1]['created_at']}|{items[-1]['id']}" if more else None}

    def active(self) -> list[dict[str, Any]]:
        return [self._run(r) for r in self._all("SELECT * FROM audit_runs WHERE state IN (?, ?)", *ACTIVE)]

    # Investigação por IA -------------------------------------------------------------------

    def request_investigation(self, run_id: str, trigger: str) -> dict[str, Any]:
        """Uma por run; ativa ou concluída é devolvida, falha/pulada/esgotada pode ser repetida."""
        with self.tx() as db:
            row = db.execute("SELECT * FROM investigations WHERE run_id = ?", (run_id,)).fetchone()
            if row is not None and row["state"] in (*INVESTIGATION_ACTIVE, "completed"):
                return {**dict(row), "created": False}
            attempt = (row["attempt"] + 1) if row is not None else 1
            db.execute("INSERT OR REPLACE INTO investigations (run_id, state, trigger, attempt, requested_at) "
                       "VALUES (?, 'queued', ?, ?, ?)", (run_id, trigger, attempt, now()))
            return {**dict(db.execute("SELECT * FROM investigations WHERE run_id = ?", (run_id,)).fetchone()),
                    "created": True}

    def next_investigation(self) -> sqlite3.Row | None:
        return self._one("SELECT * FROM investigations WHERE state = 'queued' ORDER BY requested_at LIMIT 1")

    def update_investigation(self, run_id: str, **fields: Any) -> None:
        if not fields:
            return
        columns = ", ".join(f"{name} = ?" for name in fields)
        with self.tx() as db:
            db.execute(f"UPDATE investigations SET {columns} WHERE run_id = ?", (*fields.values(), run_id))

    def investigation(self, run_id: str) -> dict[str, Any] | None:
        row = self._one("SELECT * FROM investigations WHERE run_id = ?", run_id)
        return dict(row) if row else None

    def recover_investigations(self) -> int:
        with self.tx() as db:
            return db.execute("UPDATE investigations SET state = 'interrupted', finished_at = ?, error = "
                              "'O serviço foi encerrado durante a investigação.' WHERE state IN (?, ?)",
                              (now(), *INVESTIGATION_ACTIVE)).rowcount

    def latest_finished(self) -> dict[str, Any] | None:
        row = self._one("SELECT * FROM audit_runs WHERE state IN ('completed', 'partial', 'failed') "
                        "ORDER BY created_at DESC, id DESC LIMIT 1")
        return self._run(row) if row else None
