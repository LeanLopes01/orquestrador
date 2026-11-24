"""Módulo 3: busca vetorial por tipo + leitura atual do disco para scripts C#.

Ponteiros de código sempre reabrem o arquivo; nunca há cópia retida. Chunks de
documentação são snapshots: o arquivo local precisa ter o mesmo hash indexado.
"""

from __future__ import annotations

import hashlib
import re
import time
from collections.abc import Callable
from pathlib import Path

from .code_indexer import KIND as CODE_KIND
from .code_indexer import CodeIndexer
from .config import RagConfig
from .document_indexer import KIND as DOC_KIND
from .embeddings import Embedder
from .models import RetrievalResult, RetrievedSource
from .paths import ReadError, decode_text, relative_to, stable_read, within
from .store import VectorStore

MENTION = re.compile(r"\b([A-Za-z_][\w.-]*\.cs)\b", re.IGNORECASE)


class QueryError(ValueError):
    pass


class Retriever:
    def __init__(self, config: RagConfig, embedder: Embedder, store: VectorStore, code: CodeIndexer,
                 docs_recovering: Callable[[], bool], schedule_reindex: Callable[[Path], None]) -> None:
        self.config = config
        self.embedder = embedder
        self.store = store
        self.code = code
        self.docs_recovering = docs_recovering
        self.schedule_reindex = schedule_reindex

    def _candidates(self, embedding: list[float], kind: str) -> list[dict]:
        available = self.store.count(self.config.project_id, kind)
        n = min(self.config.retrieval.candidate_cap, available)
        return self.store.query(embedding, self.store.where(self.config.project_id, kind), n)

    def _read_code(self, row: dict, warnings: list[str]) -> RetrievedSource | None:
        meta = row["metadata"]
        filepath = str(meta.get("filepath", ""))
        path = Path(filepath)
        # Não confiar cegamente na metadata: o alvo real precisa estar na raiz dos scripts.
        if not filepath or not within(self.config.scripts_root, path):
            warnings.append(f"pointer_outside_root: ponteiro ignorado ({path.name or row['id']}).")
            return None
        try:
            read = stable_read(path, max_bytes=self.config.retrieval.max_script_bytes,
                               attempts=self.config.retrieval.read_attempts)
            if not within(self.config.scripts_root, path):  # revalidado junto da abertura
                warnings.append(f"pointer_outside_root: {path.name} mudou de destino.")
                return None
            text = decode_text(read.data, self.config.chunking.fallback_encoding)
        except ReadError as exc:
            code = "source_missing" if exc.code == "missing" else "source_unreadable"
            warnings.append(f"{code}: {path.name} — {exc}")
            if exc.code == "missing":
                self.schedule_reindex(path)
            return None
        state = "current"
        if meta.get("source_hash") and meta["source_hash"] != read.sha256:
            state = "stale_summary"  # código lido agora; resumo será atualizado
            self.schedule_reindex(path)
        lines = text.count("\n") + 1
        return RetrievedSource(
            id="", record_id=row["id"], kind=CODE_KIND, filepath=str(path),
            relpath=relative_to(self.config.unity_project_root, path), text=text,
            distance=row["distance"], hash=read.sha256, read_at=read.read_at, lines=(1, lines),
            state=state, full_file=True,
            provenance={"main_class": meta.get("main_class"), "summary": row.get("document", ""),
                        "bytes": read.size},
        )

    def _doc(self, row: dict, warnings: list[str], hashes: dict[str, str | None]) -> RetrievedSource | None:
        meta = row["metadata"]
        filepath = str(meta.get("filepath", ""))
        if filepath not in hashes:
            try:
                hashes[filepath] = hashlib.sha256(Path(filepath).read_bytes()).hexdigest()
            except OSError:
                hashes[filepath] = None
        if hashes[filepath] != meta.get("doc_hash"):
            warnings.append(f"document_needs_reindex: {Path(filepath).name} mudou ou sumiu desde a indexação.")
            return None
        start, end = meta.get("line_start"), meta.get("line_end")
        keys = ("source_url", "source_type", "extracted_at", "acquired_at", "canonical_url", "final_url",
                "language", "caption", "ingestion_source_id", "doc_title", "provenance")
        return RetrievedSource(
            id="", record_id=row["id"], kind=DOC_KIND, filepath=filepath,
            relpath=str(meta.get("relpath", Path(filepath).name)), text=row["document"],
            distance=row["distance"], hash=str(meta.get("doc_hash", "")), read_at="",
            lines=(int(start), int(end)) if start and end else None, chunk_index=meta.get("chunk_index"),
            state="snapshot", section=meta.get("section"),
            provenance={k: meta[k] for k in keys if meta.get(k) is not None},
        )

    def retrieve(self, query: str) -> RetrievalResult:
        query = (query or "").strip()
        if not query:
            raise QueryError("A pergunta está vazia.")
        if len(query) > self.config.retrieval.max_query_chars:
            raise QueryError(f"A pergunta excede {self.config.retrieval.max_query_chars} caracteres.")
        timings: dict[str, int] = {}
        warnings: list[str] = []
        t0 = time.monotonic()
        embedding = self.embedder.encode([query])[0]
        timings["embedding"] = int((time.monotonic() - t0) * 1000)

        t1 = time.monotonic()
        code_rows = self._candidates(embedding, CODE_KIND)
        mentioned = []
        for name in dict.fromkeys(m.group(1) for m in MENTION.finditer(query)):
            exact = self.code.by_filename(name)
            if not exact:
                warnings.append(f"mention_not_indexed: {name} não está no índice (rode rescan se for novo).")
            mentioned.extend(exact)
        ordered, seen_ids = [], set()
        for row in [*mentioned, *code_rows]:
            if row["id"] not in seen_ids:
                seen_ids.add(row["id"])
                ordered.append(row)
        code_sources: list[RetrievedSource] = []
        files_read: list[str] = []
        bytes_read = 0
        for row in ordered:  # backfill: ignora ilegíveis e segue até a cota
            if len(code_sources) >= self.config.retrieval.code_top_k:
                break
            source = self._read_code(row, warnings)
            if source is None:
                continue
            source.provenance["mentioned"] = row in mentioned
            code_sources.append(source)
            files_read.append(source.relpath)
            bytes_read += int(source.provenance.get("bytes", 0))
        timings["code"] = int((time.monotonic() - t1) * 1000)

        t2 = time.monotonic()
        doc_sources: list[RetrievedSource] = []
        if self.docs_recovering():
            warnings.append("documents_recovering: reindexação documental incompleta; documentos suspensos.")
        else:
            hashes: dict[str, str | None] = {}
            seen_text: set[str] = set()
            per_doc_counts: dict[str, int] = {}
            per_doc_cap = max(2, self.config.retrieval.doc_top_k // 2)
            overflow: list[RetrievedSource] = []
            for row in self._candidates(embedding, DOC_KIND):
                if len(doc_sources) >= self.config.retrieval.doc_top_k:
                    break
                fingerprint = hashlib.sha256(row["document"].encode()).hexdigest()
                if fingerprint in seen_text:
                    continue
                source = self._doc(row, warnings, hashes)
                if source is None:
                    continue
                seen_text.add(fingerprint)
                count = per_doc_counts.get(source.filepath, 0)
                if count < per_doc_cap:
                    per_doc_counts[source.filepath] = count + 1
                    doc_sources.append(source)
                else:
                    overflow.append(source)
            for source in overflow:
                if len(doc_sources) >= self.config.retrieval.doc_top_k:
                    break
                doc_sources.append(source)
        timings["documents"] = int((time.monotonic() - t2) * 1000)

        sources = _interleave(code_sources, doc_sources)
        for index, source in enumerate(sources, start=1):
            source.id = f"S{index}"
        if not sources:
            warnings.append("no_context: nenhuma fonte indexada corresponde à pergunta.")
        return RetrievalResult(query, sources, list(dict.fromkeys(warnings)), bytes_read, files_read, timings)


def _interleave(code: list[RetrievedSource], docs: list[RetrievedSource]) -> list[RetrievedSource]:
    """Menções explícitas primeiro; depois alterna código/documento por relevância."""
    first = [s for s in code if s.provenance.get("mentioned")]
    rest_code = [s for s in code if not s.provenance.get("mentioned")]
    out = list(first)
    for i in range(max(len(rest_code), len(docs))):
        pair = sorted([x for x in (rest_code[i] if i < len(rest_code) else None, docs[i] if i < len(docs) else None) if x],
                      key=lambda s: s.distance)
        out.extend(pair)
    return out
