"""Estado durável da ingestão (SQLite): lotes, itens, tentativas de escrita e documentos.

O manifesto JSON é uma exportação deste estado, não uma terceira fonte de verdade.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Any

from .acquisition import now_iso
from .models import TERMINAL, SourceResult, Status
from .storage import sha256_file

SCHEMA = """
CREATE TABLE IF NOT EXISTS batches (
  id TEXT PRIMARY KEY, request_id TEXT UNIQUE, payload_hash TEXT, project_id TEXT NOT NULL,
  mode TEXT NOT NULL, state TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  total INTEGER NOT NULL DEFAULT 0, cancel_requested INTEGER NOT NULL DEFAULT 0, input_label TEXT
);
CREATE TABLE IF NOT EXISTS items (
  batch_id TEXT NOT NULL, position INTEGER NOT NULL, raw_url TEXT NOT NULL, catalog_id TEXT,
  curation TEXT, include_comments INTEGER, status TEXT NOT NULL, result TEXT, updated_at TEXT NOT NULL,
  PRIMARY KEY (batch_id, position)
);
CREATE TABLE IF NOT EXISTS writes (
  source_id TEXT PRIMARY KEY, path TEXT NOT NULL, expected_sha256 TEXT NOT NULL,
  state TEXT NOT NULL, batch_id TEXT, position INTEGER, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
  source_id TEXT PRIMARY KEY, path TEXT NOT NULL, sha256 TEXT NOT NULL, kind TEXT NOT NULL,
  original_url TEXT NOT NULL, canonical_url TEXT NOT NULL, final_url TEXT, extracted_at TEXT NOT NULL,
  acquired_at TEXT NOT NULL, cache_revision TEXT NOT NULL, options_hash TEXT NOT NULL,
  language TEXT, body_sha256 TEXT, updated_at TEXT NOT NULL
);
"""


class Repository:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=FULL")
        self._db.executescript(SCHEMA)
        self._lock = threading.RLock()

    def close(self) -> None:
        self._db.close()

    # Lotes ---------------------------------------------------------------------

    @staticmethod
    def payload_hash(payload: Any) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def find_request(self, request_id: str) -> sqlite3.Row | None:
        with self._lock:
            return self._db.execute("SELECT * FROM batches WHERE request_id=?", (request_id,)).fetchone()

    def create_batch(
        self, project_id: str, mode: str, items: list[Any], *, request_id: str | None = None,
        payload_hash: str | None = None, label: str | None = None,
    ) -> str:
        batch_id = uuid.uuid4().hex
        stamp = now_iso()
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                self._db.execute(
                    "INSERT INTO batches (id, request_id, payload_hash, project_id, mode, state, created_at,"
                    " updated_at, total, input_label) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (batch_id, request_id, payload_hash, project_id, mode, "queued", stamp, stamp, len(items), label),
                )
                for position, raw in enumerate(items):
                    self._db.execute(
                        "INSERT INTO items (batch_id, position, raw_url, catalog_id, curation, include_comments,"
                        " status, updated_at) VALUES (?,?,?,?,?,?,?,?)",
                        (batch_id, position, raw.original_url, raw.catalog_id,
                         json.dumps(raw.curation, ensure_ascii=False) if raw.curation else None,
                         None if raw.include_comments is None else int(raw.include_comments),
                         Status.QUEUED.value, stamp),
                    )
                self._db.execute("COMMIT")
            except BaseException:
                self._db.execute("ROLLBACK")
                raise
        return batch_id

    def set_batch_state(self, batch_id: str, state: str) -> None:
        with self._lock:
            self._db.execute("UPDATE batches SET state=?, updated_at=? WHERE id=?", (state, now_iso(), batch_id))

    def request_cancel(self, batch_id: str) -> bool:
        with self._lock:
            cur = self._db.execute(
                "UPDATE batches SET cancel_requested=1, updated_at=? WHERE id=? AND state IN ('queued','running')",
                (now_iso(), batch_id),
            )
            return cur.rowcount > 0

    def cancel_requested(self, batch_id: str) -> bool:
        with self._lock:
            row = self._db.execute("SELECT cancel_requested FROM batches WHERE id=?", (batch_id,)).fetchone()
            return bool(row and row[0])

    def pending_items(self, batch_id: str) -> list[sqlite3.Row]:
        terminal = tuple(s.value for s in TERMINAL)
        with self._lock:
            return self._db.execute(
                f"SELECT * FROM items WHERE batch_id=? AND status NOT IN ({','.join('?' * len(terminal))})"
                " ORDER BY position",
                (batch_id, *terminal),
            ).fetchall()

    def set_item(self, batch_id: str, position: int, status: str, result: SourceResult | None = None) -> None:
        with self._lock:
            if result is None:
                self._db.execute(
                    "UPDATE items SET status=?, updated_at=? WHERE batch_id=? AND position=?",
                    (status, now_iso(), batch_id, position),
                )
            else:
                self._db.execute(
                    "UPDATE items SET status=?, result=?, updated_at=? WHERE batch_id=? AND position=?",
                    (status, json.dumps(result.to_dict(), ensure_ascii=False), now_iso(), batch_id, position),
                )

    def batch(self, batch_id: str, *, limit: int = 200, offset: int = 0) -> dict[str, Any] | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM batches WHERE id=?", (batch_id,)).fetchone()
            if row is None:
                return None
            counts = {
                r["status"]: r["n"]
                for r in self._db.execute(
                    "SELECT status, COUNT(*) AS n FROM items WHERE batch_id=? GROUP BY status", (batch_id,)
                )
            }
            items = self._db.execute(
                "SELECT * FROM items WHERE batch_id=? ORDER BY position LIMIT ? OFFSET ?",
                (batch_id, limit, offset),
            ).fetchall()
        return {
            "id": row["id"], "request_id": row["request_id"], "project_id": row["project_id"],
            "mode": row["mode"], "state": row["state"], "created_at": row["created_at"],
            "updated_at": row["updated_at"], "total": row["total"], "input": row["input_label"],
            "cancel_requested": bool(row["cancel_requested"]),
            "counts": {
                "completed": counts.get("completed", 0), "skipped": counts.get("skipped", 0),
                "failed": counts.get("failed", 0), "cancelled": counts.get("cancelled", 0),
                "interrupted": counts.get("interrupted", 0),
                "pending": sum(n for s, n in counts.items() if s not in {t.value for t in TERMINAL}),
            },
            "items": [
                {"position": i["position"], "raw_url": i["raw_url"], "catalog_id": i["catalog_id"],
                 "status": i["status"], "result": json.loads(i["result"]) if i["result"] else None,
                 "updated_at": i["updated_at"]}
                for i in items
            ],
            "limit": limit, "offset": offset,
        }

    def batches(self, *, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT id FROM batches ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)
            ).fetchall()
        out = []
        for row in rows:
            summary = self.batch(row["id"], limit=0)
            if summary:
                summary.pop("items")
                out.append(summary)
        return out

    def next_queued(self) -> str | None:
        with self._lock:
            row = self._db.execute(
                "SELECT id FROM batches WHERE state='queued' ORDER BY created_at LIMIT 1"
            ).fetchone()
            return row["id"] if row else None

    # Publicação de documentos ---------------------------------------------------

    def begin_write(self, source_id: str, path: str, expected: str, batch_id: str | None, position: int | None) -> None:
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO writes (source_id, path, expected_sha256, state, batch_id, position,"
                " updated_at) VALUES (?,?,?,?,?,?,?)",
                (source_id, path, expected, "writing", batch_id, position, now_iso()),
            )

    def finish_write(self, source_id: str, document: dict[str, Any]) -> None:
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                self._db.execute(
                    "INSERT OR REPLACE INTO documents (source_id, path, sha256, kind, original_url, canonical_url,"
                    " final_url, extracted_at, acquired_at, cache_revision, options_hash, language, body_sha256,"
                    " updated_at) VALUES (:source_id,:path,:sha256,:kind,:original_url,:canonical_url,:final_url,"
                    ":extracted_at,:acquired_at,:cache_revision,:options_hash,:language,:body_sha256,:updated_at)",
                    {**document, "updated_at": now_iso()},
                )
                self._db.execute("UPDATE writes SET state='completed', updated_at=? WHERE source_id=?", (now_iso(), source_id))
                self._db.execute("COMMIT")
            except BaseException:
                self._db.execute("ROLLBACK")
                raise

    def abort_write(self, source_id: str) -> None:
        with self._lock:
            self._db.execute("UPDATE writes SET state='failed', updated_at=? WHERE source_id=?", (now_iso(), source_id))

    def document(self, source_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM documents WHERE source_id=?", (source_id,)).fetchone()
        return dict(row) if row else None

    def documents(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(r) for r in self._db.execute("SELECT * FROM documents ORDER BY updated_at DESC")]

    # Recuperação após queda ---------------------------------------------------------

    def recover(self) -> dict[str, int]:
        """`writing` confirmado pelo hash vira completed; o resto não concluído vira interrupted."""
        confirmed = interrupted = 0
        with self._lock:
            for row in self._db.execute("SELECT * FROM writes WHERE state='writing'").fetchall():
                if sha256_file(Path(row["path"])) == row["expected_sha256"]:
                    # O arquivo foi publicado mas o documento não foi registrado: o item
                    # volta a ser processado como no-op na retomada, sem reescrever.
                    self._db.execute("UPDATE writes SET state='published_unconfirmed' WHERE source_id=?", (row["source_id"],))
                    confirmed += 1
                else:
                    self._db.execute("UPDATE writes SET state='failed' WHERE source_id=?", (row["source_id"],))
            terminal = tuple(s.value for s in TERMINAL)
            cur = self._db.execute(
                f"UPDATE items SET status='interrupted', updated_at=? WHERE status NOT IN ({','.join('?' * len(terminal))})"
                " AND batch_id IN (SELECT id FROM batches WHERE state='running')",
                (now_iso(), *terminal),
            )
            interrupted = cur.rowcount
            self._db.execute("UPDATE batches SET state='interrupted', updated_at=? WHERE state='running'", (now_iso(),))
        return {"confirmed_writes": confirmed, "interrupted_items": interrupted}

    def resume(self, batch_id: str) -> bool:
        """Itens interrupted voltam para a fila; sucessos são preservados."""
        with self._lock:
            row = self._db.execute("SELECT state FROM batches WHERE id=?", (batch_id,)).fetchone()
            if row is None or row["state"] not in {"interrupted", "cancelled"}:
                return False
            self._db.execute(
                "UPDATE items SET status='queued', updated_at=? WHERE batch_id=? AND status IN ('interrupted','cancelled')",
                (now_iso(), batch_id),
            )
            self._db.execute(
                "UPDATE batches SET state='queued', cancel_requested=0, updated_at=? WHERE id=?", (now_iso(), batch_id)
            )
            return True
