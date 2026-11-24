"""Estado da descoberta (SQLite): cada fonte proposta uma vez, com estratégia, motivo e destino.

Estados: proposed → submitted → ingested | failed | skipped. `rejected` é decisão do
usuário e nunca volta a ser proposto. Documentos já publicados pela ingestão são lidos
direto do estado dela (somente leitura).
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS candidates (
  source_id TEXT PRIMARY KEY, url TEXT NOT NULL, title TEXT NOT NULL, catalog TEXT NOT NULL,
  strategy TEXT NOT NULL, score REAL NOT NULL, reason TEXT NOT NULL, status TEXT NOT NULL,
  batch_id TEXT, detail TEXT, run_id TEXT, created_at REAL NOT NULL, updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY, started_at REAL NOT NULL, finished_at REAL, state TEXT NOT NULL,
  summary TEXT
);
"""
FINAL = {"ingested", "failed", "skipped", "rejected"}


class Store:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path), isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript(SCHEMA)

    def close(self) -> None:
        self._db.close()

    def known_ids(self) -> set[str]:
        """Já tratados: não são propostos de novo. `proposed` antigo pode ser reproposto."""
        rows = self._db.execute("SELECT source_id FROM candidates WHERE status != 'proposed'").fetchall()
        return {r["source_id"] for r in rows}

    def propose(self, run_id: str, candidates: list[Any]) -> None:
        now = time.time()
        for c in candidates:
            self._db.execute(
                "INSERT INTO candidates (source_id, url, title, catalog, strategy, score, reason, status, run_id,"
                " created_at, updated_at) VALUES (?,?,?,?,?,?,?,'proposed',?,?,?)"
                " ON CONFLICT(source_id) DO UPDATE SET score=excluded.score, reason=excluded.reason,"
                " run_id=excluded.run_id, updated_at=excluded.updated_at WHERE status='proposed'",
                (c.source_id, c.url, c.title, c.catalog, c.strategy, c.score, c.reason, run_id, now, now),
            )

    def set_status(self, source_id: str, status: str, *, batch_id: str | None = None,
                   detail: str | None = None) -> None:
        self._db.execute(
            "UPDATE candidates SET status=?, batch_id=COALESCE(?, batch_id), detail=COALESCE(?, detail),"
            " updated_at=? WHERE source_id=?",
            (status, batch_id, detail, time.time(), source_id),
        )

    def reject(self, needle: str) -> int:
        cursor = self._db.execute(
            "UPDATE candidates SET status='rejected', updated_at=? WHERE (source_id=? OR url=?)"
            " AND status IN ('proposed','failed','skipped')", (time.time(), needle, needle),
        )
        return cursor.rowcount

    def candidates(self, status: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        if status:
            rows = self._db.execute(
                "SELECT * FROM candidates WHERE status=? ORDER BY updated_at DESC LIMIT ?", (status, limit))
        else:
            rows = self._db.execute("SELECT * FROM candidates ORDER BY updated_at DESC LIMIT ?", (limit,))
        return [dict(r) for r in rows.fetchall()]

    def counts(self) -> dict[str, int]:
        return {r["status"]: r["n"] for r in
                self._db.execute("SELECT status, COUNT(*) AS n FROM candidates GROUP BY status")}

    def start_run(self, run_id: str) -> None:
        self._db.execute("INSERT INTO runs (id, started_at, state) VALUES (?,?,'running')", (run_id, time.time()))

    def finish_run(self, run_id: str, state: str, summary: str) -> None:
        self._db.execute("UPDATE runs SET finished_at=?, state=?, summary=? WHERE id=?",
                         (time.time(), state, summary, run_id))


def _read_only(path: Path) -> sqlite3.Connection | None:
    if not path.exists():
        return None
    db = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def ingested_source_ids(ingestion_state: Path) -> set[str]:
    db = _read_only(ingestion_state)
    if db is None:
        return set()
    try:
        return {r["source_id"] for r in db.execute("SELECT source_id FROM documents")}
    except sqlite3.Error:
        return set()
    finally:
        db.close()


def ingested_titles(ingestion_state: Path, limit: int = 60) -> list[str]:
    """Títulos (1ª linha '# ') dos documentos publicados, para o prompt saber o que já existe."""
    db = _read_only(ingestion_state)
    if db is None:
        return []
    try:
        paths = [r["path"] for r in db.execute("SELECT path FROM documents ORDER BY updated_at DESC LIMIT ?",
                                                (limit,))]
    except sqlite3.Error:
        return []
    finally:
        db.close()
    titles = []
    for path in paths:
        try:
            with open(path, encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("# "):
                        titles.append(line[2:].strip())
                        break
        except OSError:
            continue
    return titles


def recent_questions(rag_state: Path, limit: int = 20) -> list[str]:
    """Perguntas recentes feitas ao RAG (expiram com o TTL do serviço)."""
    db = _read_only(rag_state)
    if db is None:
        return []
    try:
        rows = db.execute("SELECT query FROM asks ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return list(dict.fromkeys(r["query"].strip() for r in rows if r["query"].strip()))
    except sqlite3.Error:
        return []
    finally:
        db.close()
