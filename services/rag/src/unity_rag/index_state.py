"""Journal SQLite do índice, jobs e pedidos (asks).

Não existe transação atômica entre SQLite e Chroma: documentos passam por
dirty → mutação no Chroma → verificação → clean. Enquanto houver dirty, a busca
documental fica suspensa (documents_recovering) e a inicialização reconcilia.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS code_files (
  path_key TEXT PRIMARY KEY, filepath TEXT NOT NULL, record_id TEXT NOT NULL, summary_hash TEXT,
  source_hash TEXT, mtime_ns INTEGER, size INTEGER, state TEXT NOT NULL, error TEXT, updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
  path_key TEXT PRIMARY KEY, filepath TEXT NOT NULL, doc_hash TEXT, chunk_ids TEXT NOT NULL DEFAULT '[]',
  state TEXT NOT NULL, error TEXT, updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY, scope TEXT NOT NULL, state TEXT NOT NULL, created_at REAL NOT NULL,
  updated_at REAL NOT NULL, progress TEXT, report TEXT, error TEXT
);
CREATE TABLE IF NOT EXISTS asks (
  id TEXT PRIMARY KEY, request_id TEXT UNIQUE, query TEXT NOT NULL, state TEXT NOT NULL,
  created_at REAL NOT NULL, updated_at REAL NOT NULL, progress TEXT, result TEXT, error TEXT
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


class IndexState:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=NORMAL")
        self._db.executescript(SCHEMA)
        self._lock = threading.RLock()

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def meta(self, key: str, default: str | None = None) -> str | None:
        with self._lock:
            row = self._db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_meta(self, key: str, value: str) -> None:
        with self._lock:
            self._db.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?,?)", (key, value))

    # Código ---------------------------------------------------------------------

    def code_file(self, path_key: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM code_files WHERE path_key=?", (path_key,)).fetchone()
        return dict(row) if row else None

    def code_files(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(r) for r in self._db.execute("SELECT * FROM code_files")]

    def put_code_file(self, **row: Any) -> None:
        row.setdefault("error", None)
        row["updated_at"] = time.time()
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO code_files (path_key, filepath, record_id, summary_hash, source_hash,"
                " mtime_ns, size, state, error, updated_at) VALUES (:path_key,:filepath,:record_id,:summary_hash,"
                ":source_hash,:mtime_ns,:size,:state,:error,:updated_at)",
                row,
            )

    def drop_code_file(self, path_key: str) -> None:
        with self._lock:
            self._db.execute("DELETE FROM code_files WHERE path_key=?", (path_key,))

    # Documentos -------------------------------------------------------------------

    def document(self, path_key: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM documents WHERE path_key=?", (path_key,)).fetchone()
        if row is None:
            return None
        data = dict(row)
        data["chunk_ids"] = json.loads(data["chunk_ids"])
        return data

    def documents(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = [dict(r) for r in self._db.execute("SELECT * FROM documents")]
        for row in rows:
            row["chunk_ids"] = json.loads(row["chunk_ids"])
        return rows

    def mark_document_dirty(self, path_key: str, filepath: str, previous_ids: list[str], new_ids: list[str]) -> None:
        """Confirmado antes da primeira mutação no Chroma: guarda os IDs antigos e novos."""
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO documents (path_key, filepath, doc_hash, chunk_ids, state, error, updated_at)"
                " VALUES (?,?,?,?,?,?,?)",
                (path_key, filepath, None, json.dumps(sorted(set(previous_ids) | set(new_ids))), "dirty", None, time.time()),
            )

    def mark_document_clean(self, path_key: str, filepath: str, doc_hash: str, chunk_ids: list[str]) -> None:
        with self._lock:
            self._db.execute(
                "UPDATE documents SET filepath=?, doc_hash=?, chunk_ids=?, state='clean', error=NULL, updated_at=?"
                " WHERE path_key=?",
                (filepath, doc_hash, json.dumps(chunk_ids), time.time(), path_key),
            )

    def mark_document_error(self, path_key: str, error: str) -> None:
        with self._lock:
            self._db.execute("UPDATE documents SET error=?, updated_at=? WHERE path_key=?", (error, time.time(), path_key))

    def drop_document(self, path_key: str) -> None:
        with self._lock:
            self._db.execute("DELETE FROM documents WHERE path_key=?", (path_key,))

    def dirty_documents(self) -> list[dict[str, Any]]:
        return [d for d in self.documents() if d["state"] == "dirty"]

    # Jobs e asks -------------------------------------------------------------------

    def create_job(self, scope: str) -> str:
        job_id = uuid.uuid4().hex
        now = time.time()
        with self._lock:
            self._db.execute("INSERT INTO jobs (id, scope, state, created_at, updated_at) VALUES (?,?,?,?,?)",
                             (job_id, scope, "queued", now, now))
        return job_id

    def update_job(self, job_id: str, *, state: str | None = None, progress: dict | None = None,
                   report: dict | None = None, error: str | None = None) -> None:
        sets, values = ["updated_at=?"], [time.time()]
        for name, value in (("state", state), ("progress", progress), ("report", report), ("error", error)):
            if value is not None:
                sets.append(f"{name}=?")
                values.append(json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value)
        with self._lock:
            self._db.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE id=?", (*values, job_id))

    def job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return _decode(row, ("progress", "report"))

    def create_ask(self, request_id: str | None, query: str) -> tuple[str, bool]:
        """(ask_id, criado). Repetir o mesmo request_id devolve o pedido existente."""
        with self._lock:
            if request_id:
                row = self._db.execute("SELECT id FROM asks WHERE request_id=?", (request_id,)).fetchone()
                if row:
                    return row["id"], False
            ask_id = uuid.uuid4().hex
            now = time.time()
            self._db.execute(
                "INSERT INTO asks (id, request_id, query, state, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                (ask_id, request_id, query, "queued", now, now),
            )
            return ask_id, True

    def update_ask(self, ask_id: str, *, state: str | None = None, progress: dict | None = None,
                   result: dict | None = None, error: str | None = None) -> None:
        sets, values = ["updated_at=?"], [time.time()]
        for name, value in (("state", state), ("progress", progress), ("result", result), ("error", error)):
            if value is not None:
                sets.append(f"{name}=?")
                values.append(json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value)
        with self._lock:
            self._db.execute(f"UPDATE asks SET {', '.join(sets)} WHERE id=?", (*values, ask_id))

    def ask(self, ask_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM asks WHERE id=?", (ask_id,)).fetchone()
        return _decode(row, ("progress", "result"))

    def ask_by_request(self, request_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM asks WHERE request_id=?", (request_id,)).fetchone()
        return _decode(row, ("progress", "result"))

    def recent_asks(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT id, request_id, query, state, created_at, updated_at, error FROM asks"
                " ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def interrupt_running(self) -> int:
        """Reinício: trabalhos em execução viram interrupted, sem repetir geração."""
        now = time.time()
        with self._lock:
            a = self._db.execute(
                "UPDATE jobs SET state='interrupted', updated_at=? WHERE state IN ('queued','running')", (now,)
            ).rowcount
            b = self._db.execute(
                "UPDATE asks SET state='interrupted', updated_at=?, error='O serviço reiniciou antes do fim.'"
                " WHERE state IN ('queued','running')", (now,)
            ).rowcount
        return a + b

    def expire(self, ttl_seconds: float) -> None:
        cutoff = time.time() - ttl_seconds
        with self._lock:
            self._db.execute("DELETE FROM asks WHERE updated_at < ? AND state NOT IN ('queued','running')", (cutoff,))
            self._db.execute("DELETE FROM jobs WHERE updated_at < ? AND state NOT IN ('queued','running')", (cutoff,))


def _decode(row: sqlite3.Row | None, fields: tuple[str, ...]) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    for name in fields:
        if data.get(name):
            try:
                data[name] = json.loads(data[name])
            except ValueError:
                pass
    return data
