"""Caminhos finais e escrita atômica: o indexador só vê arquivos concluídos."""

from __future__ import annotations

import hashlib
import os
import secrets
from pathlib import Path

from .models import SourceFailure, SourceSpec, Status, StoredDocument


def document_name(source: SourceSpec) -> str:
    # Nunca a partir do título remoto.
    return f"video-{source.video_id}.md" if source.kind == "video" else f"artigo-{source.source_id}.md"


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return None


def write_document_atomic(markdown: str, name: str, output_root: Path) -> StoredDocument:
    data = markdown.encode("utf-8")
    if not markdown.strip():
        raise SourceFailure(Status.SKIPPED, "content_unavailable", "Documento vazio não é publicado.")
    try:
        output_root.mkdir(parents=True, exist_ok=True)
        target = output_root / name
        tmp = output_root / f".tmp-{name}-{secrets.token_hex(4)}"
        try:
            with open(tmp, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, target)
        finally:
            tmp.unlink(missing_ok=True)
    except OSError as exc:
        raise SourceFailure(Status.FAILED, "storage_error", f"Falha ao gravar o documento: {exc.strerror or exc}.") from None
    return StoredDocument(str(target), hashlib.sha256(data).hexdigest(), len(data))


def clean_temporaries(output_root: Path) -> int:
    removed = 0
    if output_root.is_dir():
        for tmp in output_root.glob(".tmp-*"):
            tmp.unlink(missing_ok=True)
            removed += 1
    return removed
