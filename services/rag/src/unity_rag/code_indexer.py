"""Pointer RAG: o Chroma guarda só o resumo (nome, classe, comentários) e o ponteiro.

O código C# integral nunca é persistido na coleção; a busca lê o arquivo atual do
disco a cada consulta (retrieval.py).
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path

from . import SCHEMA_VERSION
from .config import RagConfig
from .csharp_summary import CSharpSummary, summarize
from .embeddings import Embedder
from .index_state import IndexState
from .models import IndexReport
from .paths import ReadError, canonical_key, decode_text, ignored_part, is_temporary, record_id, stable_read, within
from .store import VectorStore

logger = logging.getLogger("unity_rag")
KIND = "code_pointer"


class RootUnavailable(Exception):
    pass


def is_script(path: Path) -> bool:
    return path.suffix.lower() == ".cs" and not is_temporary(path.name)


class CodeIndexer:
    def __init__(self, config: RagConfig, embedder: Embedder, store: VectorStore, state: IndexState) -> None:
        self.config = config
        self.embedder = embedder
        self.store = store
        self.state = state
        self.root = config.scripts_root

    def record_id(self, path: Path) -> str:
        return record_id("code", self.config.project_id, path)

    def in_scope(self, path: Path) -> bool:
        if not is_script(path) or not within(self.root, path):
            return False
        try:
            relative = Path(os.path.realpath(path)).relative_to(Path(os.path.realpath(self.root)))
        except ValueError:
            return False
        return not ignored_part(relative.parts[:-1])

    def scan(self) -> list[Path]:
        if not self.root.is_dir():
            raise RootUnavailable(f"Raiz de scripts inacessível: {self.root}")
        found: list[Path] = []
        errors: list[OSError] = []

        def onerror(exc: OSError) -> None:
            errors.append(exc)

        for dirpath, dirnames, filenames in os.walk(self.root, onerror=onerror):
            dirnames[:] = [d for d in dirnames if d.lower() not in {"library", "temp", "obj", "bin"} and not d.startswith(".")]
            for name in filenames:
                path = Path(dirpath) / name
                if self.in_scope(path):
                    found.append(path)
        if errors and not found:
            raise RootUnavailable(f"Falha ao listar {self.root}: {errors[0]}")
        return found

    def _summary_text(self, summary: CSharpSummary) -> tuple[str, bool]:
        text = summary.text()
        limit = self.embedder.max_tokens
        if self.embedder.count_tokens(text) <= limit:
            return text, False
        # Preserva nome/classe; corta só a descrição, sinalizando o corte.
        base = summary.text("")
        room = max(0, limit - self.embedder.count_tokens(base + " Descrição:  [comentário truncado]"))
        spans = self.embedder.token_spans(summary.description)
        cut = spans[room - 1][1] if room and spans else 0
        return summary.text(summary.description[:cut].rstrip() + " [comentário truncado]"), True

    def index_file(self, path: Path) -> str:
        """added | updated | metadata | unchanged | error:<código>."""
        key = canonical_key(path)
        try:
            read = stable_read(path, max_bytes=self.config.retrieval.max_script_bytes,
                               attempts=self.config.retrieval.read_attempts)
            src = decode_text(read.data, self.config.chunking.fallback_encoding)
        except ReadError as exc:
            if exc.code == "missing":
                self.remove_path(path)
                return "removed"
            previous = self.state.code_file(key) or {}
            self.state.put_code_file(
                path_key=key, filepath=str(path), record_id=self.record_id(path),
                summary_hash=previous.get("summary_hash"), source_hash=previous.get("source_hash"),
                mtime_ns=previous.get("mtime_ns"), size=previous.get("size"), state="error", error=str(exc),
            )
            logger.debug("não indexado %s: %s", path, exc)
            return f"error:{exc.code}"
        summary = summarize(src, path.name)
        text, truncated = self._summary_text(summary)
        summary_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        rid = self.record_id(path)
        previous = self.state.code_file(key)
        metadata = {
            "kind": KIND, "project_id": self.config.project_id, "filepath": str(Path(os.path.realpath(path))),
            "filename": path.name, "filename_lower": path.name.lower(), "main_class": summary.main_class,
            "summary_hash": summary_hash, "source_hash": read.sha256, "mtime_ns": read.mtime_ns,
            "schema_version": SCHEMA_VERSION, "embedding_model": self.embedder.name,
            "summary_truncated": truncated or None,
        }
        if previous and previous.get("summary_hash") == summary_hash and previous.get("state") == "indexed":
            if previous.get("source_hash") == read.sha256:
                return "unchanged"
            # Só o corpo mudou: atualiza o frescor sem recalcular o embedding.
            self.store.update_metadata([rid], [metadata])
            outcome = "metadata"
        else:
            vector = self.embedder.encode([text])[0]
            self.store.upsert([rid], [vector], [text], [metadata])
            outcome = "updated" if previous else "added"
        self.state.put_code_file(path_key=key, filepath=str(path), record_id=rid, summary_hash=summary_hash,
                                 source_hash=read.sha256, mtime_ns=read.mtime_ns, size=read.size, state="indexed")
        return outcome

    def remove_path(self, path: Path | str) -> bool:
        key = canonical_key(path)
        row = self.state.code_file(key)
        rid = row["record_id"] if row else self.record_id(Path(path))
        self.store.delete([rid])
        self.state.drop_code_file(key)
        return row is not None

    def remove_subtree(self, directory: Path | str) -> int:
        prefix = canonical_key(directory).rstrip("\\/") + os.sep
        removed = 0
        for row in self.state.code_files():
            if row["path_key"].startswith(prefix):
                self.store.delete([row["record_id"]])
                self.state.drop_code_file(row["path_key"])
                removed += 1
        return removed

    def reconcile(self) -> IndexReport:
        """Varredura completa. Raiz inacessível nunca é tratada como exclusão em massa."""
        report = IndexReport("code")
        try:
            files = self.scan()
        except RootUnavailable as exc:
            report.errors.append(str(exc))
            return report
        present = {canonical_key(p): p for p in files}
        for row in self.state.code_files():
            if row["path_key"] not in present and not Path(row["filepath"]).exists():
                self.store.delete([row["record_id"]])
                self.state.drop_code_file(row["path_key"])
                report.removed += 1
        # Ponteiros no Chroma sem registro no journal (ex.: queda entre as escritas).
        known = {row["record_id"] for row in self.state.code_files()} | {self.record_id(p) for p in files}
        stored = set(self.store.ids(self.store.where(self.config.project_id, KIND)))
        orphans = [rid for rid in stored if rid not in known]
        self.store.delete(orphans)
        report.removed += len(orphans)
        for key, path in present.items():
            row = self.state.code_file(key)
            try:
                stat = path.stat()
            except OSError:
                continue
            if row and row["record_id"] not in stored:
                # Journal diz indexado, mas o vetor não existe (base recriada/perdida).
                self.state.drop_code_file(key)
                row = None
            if row and row["state"] == "indexed" and row["mtime_ns"] == stat.st_mtime_ns and row["size"] == stat.st_size:
                report.skipped += 1
                continue
            outcome = self.index_file(path)
            if outcome == "added":
                report.added += 1
            elif outcome in {"updated", "metadata"}:
                report.updated += 1
            elif outcome.startswith("error:"):
                report.errors.append(f"{path.name}: {outcome[6:]}")
            else:
                report.skipped += 1
        return report

    def by_filename(self, filename: str) -> list[dict]:
        rows = self.store.get(where=self.store.where(self.config.project_id, KIND, filename_lower=filename.lower()))
        return [{"id": rid, "metadata": meta or {}, "document": doc or "", "distance": 0.0}
                for rid, meta, doc in zip(rows["ids"], rows["metadatas"], rows["documents"])]
