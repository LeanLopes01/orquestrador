"""Módulo 2: indexação explícita de .md/.txt em chunks com proveniência.

Fronteira com a ingestão: um .md concluído em docs_root. O cabeçalho (Fonte, Tipo,
Data de Extração, ...) vira metadata de cada chunk e não entra no embedding.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import SCHEMA_VERSION
from .config import RagConfig
from .embeddings import Embedder
from .document_extract import SUPPORTED, extract_text
from .index_state import IndexState
from .models import IndexReport
from .paths import ReadError, canonical_key, ignored_part, is_temporary, stable_read, within
from .store import VectorStore

logger = logging.getLogger("unity_rag")
KIND = "documentation"
MAX_DOC_BYTES = 512 * 1024 * 1024
HEADER_FIELDS = {
    "Fonte": "source_url",
    "Tipo": "source_type",
    "Data de Extração": "extracted_at",
    "Source ID": "ingestion_source_id",
    "URL Canônica": "canonical_url",
    "URL Final": "final_url",
    "Aquisição Original": "acquired_at",
    "Idioma": "language",
    "Legenda": "caption",
}
SOURCE_TYPES = {"artigo": "article", "vídeo": "video", "video": "video"}
TITLE_TOKENS = 24


@dataclass
class Chunk:
    index: int
    text: str
    section: str
    line_start: int
    line_end: int
    embed_text: str


def parse_header(text: str) -> tuple[dict[str, str], str, int]:
    """(metadata, corpo, deslocamento do corpo). Só o bloco inicial até o primeiro `---` isolado."""
    lines = text.split("\n")
    fields: dict[str, str] = {}
    for index, line in enumerate(lines[:40]):
        stripped = line.strip()
        if stripped == "---":
            if not {"Fonte", "Tipo", "Data de Extração"} <= fields.keys():
                return {}, text, 0
            offset = sum(len(item) + 1 for item in lines[: index + 1])
            meta = {HEADER_FIELDS[k]: v for k, v in fields.items() if k in HEADER_FIELDS and v}
            if "source_type" in meta:
                meta["source_type"] = SOURCE_TYPES.get(meta["source_type"].lower(), meta["source_type"].lower())
            return meta, text[offset:], offset
        if not stripped:
            continue
        name, sep, value = line.partition(":")
        if not sep or not name.strip() or name.strip() != name.strip().lstrip("#"):
            return {}, text, 0
        fields[name.strip()] = value.strip()
    return {}, text, 0


def _sections(body: str) -> list[tuple[str, int, int]]:
    """(título, início, fim) por heading Markdown fora de blocos de código."""
    marks: list[tuple[str, int]] = []
    fenced = False
    position = 0
    for line in body.split("\n"):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced:
            match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
            if match:
                marks.append((match.group(2), position))
        position += len(line) + 1
    if not marks or marks[0][1] > 0:
        marks.insert(0, ("", 0))
    out = []
    for i, (title, start) in enumerate(marks):
        end = marks[i + 1][1] if i + 1 < len(marks) else len(body)
        if body[start:end].strip():
            out.append((title, start, end))
    return out


def chunk_document(body: str, body_offset: int, full_text: str, title: str, embedder: Embedder,
                   chunk_tokens: int, overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    for section, start, end in _sections(body):
        prefix_raw = " › ".join(p for p in (title, section) if p)
        prefix_spans = embedder.token_spans(prefix_raw)
        prefix = prefix_raw[: prefix_spans[TITLE_TOKENS - 1][1]] if len(prefix_spans) > TITLE_TOKENS else prefix_raw
        room = embedder.max_tokens - (embedder.count_tokens(prefix) + 2 if prefix else 0)
        size = max(16, min(chunk_tokens, room))
        step_overlap = min(overlap, size // 3)
        text = body[start:end]
        spans = embedder.token_spans(text)
        if not spans:
            continue
        s = 0
        while s < len(spans):
            e = min(s + size, len(spans))
            if e < len(spans):  # prefere cortar numa quebra de parágrafo
                for k in range(e, s + size // 2, -1):
                    if "\n\n" in text[spans[k - 1][1]:spans[k][0]]:
                        e = k
                        break
            a, b = spans[s][0], spans[e - 1][1]
            content = text[a:b]
            absolute = body_offset + start + a
            line_start = full_text.count("\n", 0, absolute) + 1
            line_end = line_start + content.count("\n")
            chunks.append(Chunk(len(chunks), content, section, line_start, line_end,
                                f"{prefix}\n{content}" if prefix else content))
            if e >= len(spans):
                break
            s = max(e - step_overlap, s + 1)
    return chunks


class DocumentIndexer:
    def __init__(self, config: RagConfig, embedder: Embedder, store: VectorStore, state: IndexState) -> None:
        self.config = config
        self.embedder = embedder
        self.store = store
        self.state = state
        self.root = config.docs_root

    @property
    def recovering(self) -> bool:
        return bool(self.state.dirty_documents())

    def chunk_ids(self, path: Path, count: int) -> list[str]:
        base = hashlib.sha256(f"{self.config.project_id}\0{canonical_key(path)}".encode()).hexdigest()
        return [f"doc:{base}:{i}" for i in range(count)]

    def scan(self) -> list[Path]:
        if not self.root.is_dir():
            raise FileNotFoundError(f"Pasta de documentos inexistente: {self.root}")
        files = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d.lower() not in {"manifests", "logs", "cache"} and within(self.root, Path(dirpath) / d) and not (Path(dirpath) / d).is_symlink() and not getattr(Path(dirpath) / d, 'is_junction', lambda: False)()]
            for name in filenames:
                path = Path(dirpath) / name
                if path.suffix.lower() in SUPPORTED and not is_temporary(name) and within(self.root, path):
                    relative = path.relative_to(self.root)
                    if not ignored_part(relative.parts[:-1]):
                        files.append(path)
        return sorted(files)

    def _existing_ids(self, key: str) -> list[str]:
        return self.store.ids(self.store.where(self.config.project_id, KIND, path_key=key))

    def index_file(self, path: Path, *, force: bool = False) -> str:
        if not within(self.root, path):
            raise ReadError('outside_root', 'Arquivo fora da pasta de documentos.')
        key = canonical_key(path)
        row = self.state.document(key)
        read = stable_read(path, max_bytes=MAX_DOC_BYTES, attempts=self.config.retrieval.read_attempts)
        if row and not force and row["state"] == "clean" and row["doc_hash"] == read.sha256:
            if len(self.store.get(ids=row["chunk_ids"], include=[])["ids"]) == len(row["chunk_ids"]):
                return "unchanged"
            force = True  # chunks perdidos na base: reindexa
        text = extract_text(path, read.data, self.config.chunking.fallback_encoding)
        meta, body, offset = parse_header(text)
        heading = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        title = heading.group(1).strip() if heading else path.stem
        chunks = chunk_document(body, offset, text, title, self.embedder, self.config.chunking.chunk_tokens,
                                self.config.chunking.overlap_tokens)
        # Embeddings preparados antes do lock e da marcação dirty.
        vectors = self.embedder.encode([c.embed_text for c in chunks])
        new_ids = self.chunk_ids(path, len(chunks))
        previous = sorted(set(row["chunk_ids"] if row else []) | set(self._existing_ids(key)))
        self.state.mark_document_dirty(key, str(path), previous, new_ids)
        provenance = {
            "kind": KIND, "project_id": self.config.project_id, "path_key": key,
            "filepath": str(Path(os.path.realpath(path))), "relpath": path.relative_to(self.root).as_posix(),
            "doc_hash": read.sha256, "doc_title": title, "schema_version": SCHEMA_VERSION,
            "embedding_model": self.embedder.name, "chunk_count": len(chunks),
            "provenance": "ingestion" if meta else "local", "source_format": path.suffix.lower(), **meta,
        }
        metadatas: list[dict[str, Any]] = [
            {**provenance, "chunk_index": c.index, "section": c.section or None,
             "line_start": c.line_start, "line_end": c.line_end}
            for c in chunks
        ]
        with self.store.lock:
            self.store.upsert(new_ids, vectors, [c.text for c in chunks], metadatas)
            stale = [i for i in previous if i not in set(new_ids)]
            self.store.delete(stale)
            check = self.store.get(ids=new_ids, include=["metadatas"])
            ok = len(check["ids"]) == len(new_ids) and all(
                (m or {}).get("doc_hash") == read.sha256 for m in check["metadatas"]
            )
            leftovers = [i for i in self._existing_ids(key) if i not in set(new_ids)]
            if not ok or leftovers:
                self.state.mark_document_error(key, "verificação pós-escrita falhou")
                raise RuntimeError(f"Verificação da substituição de {path.name} falhou; documento fica dirty.")
            self.state.mark_document_clean(key, str(path), read.sha256, new_ids)
        return "updated" if row else "added"

    def remove(self, key: str, filepath: str) -> None:
        row = self.state.document(key)
        ids = sorted(set(row["chunk_ids"] if row else []) | set(self._existing_ids(key)))
        self.state.mark_document_dirty(key, filepath, ids, [])
        with self.store.lock:
            self.store.delete(ids)
            self.state.drop_document(key)

    def recover(self) -> IndexReport:
        report = IndexReport("documents-recovery")
        for row in self.state.dirty_documents():
            path = Path(row["filepath"])
            try:
                if path.exists():
                    self.index_file(path, force=True)
                    report.updated += 1
                else:
                    self.remove(row["path_key"], row["filepath"])
                    report.removed += 1
            except (ReadError, OSError, RuntimeError) as exc:
                report.errors.append(f"{path.name}: {exc}")
        return report

    def index_documents(self, root: Path | None = None) -> IndexReport:
        if root is not None:
            self.root = root
        report = IndexReport("documents")
        recovery = self.recover()
        report.errors.extend(recovery.errors)
        try:
            files = self.scan()
        except OSError as exc:
            report.errors.append(str(exc))
            return report
        present = {canonical_key(p) for p in files}
        for path in files:
            try:
                outcome = self.index_file(path)
            except (ReadError, OSError, RuntimeError) as exc:
                report.errors.append(f"{path.name}: {exc}")
                continue
            if outcome == "added":
                report.added += 1
            elif outcome == "updated":
                report.updated += 1
            else:
                report.skipped += 1
        # Limpeza só depois de uma varredura bem-sucedida.
        for row in self.state.documents():
            if row["path_key"] not in present and not Path(row["filepath"]).exists():
                self.remove(row["path_key"], row["filepath"])
                report.removed += 1
        return report
