"""Entradas aceitas: lista .txt, manifesto JSON v1 da UI e catálogo .md com bloco JSON.

Erro global (InputError) somente quando o arquivo/esquema é ilegível; URLs inválidas
dentro de um lote válido viram falhas por item no pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import RawSource

MAX_SOURCES = 200
CATALOG_START = "<!-- RAG_SOURCE_CATALOG_START -->"
CATALOG_END = "<!-- RAG_SOURCE_CATALOG_END -->"
CATALOG_SCHEMA = "rag-source-catalog/v1"


class InputError(Exception):
    pass


def _limit(items: list[RawSource]) -> list[RawSource]:
    if len(items) > MAX_SOURCES:
        raise InputError(f"O lote aceita até {MAX_SOURCES} fontes; recebidas {len(items)}.")
    return items


def from_text(text: str) -> list[RawSource]:
    return _limit([RawSource(line.strip()) for line in text.splitlines() if line.strip()])


def from_manifest(data: Any) -> list[RawSource]:
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise InputError("Manifesto desconhecido: esperado schema_version 1.")
    sources = data.get("sources")
    if not isinstance(sources, list):
        raise InputError("Manifesto sem lista sources.")
    if len(sources) > MAX_SOURCES:
        raise InputError(f"O lote aceita até {MAX_SOURCES} fontes; recebidas {len(sources)}.")
    items = []
    for entry in sources:
        # Só a URL original é usada: kind/canonical/video_id são recalculados.
        url = entry.get("original_url") if isinstance(entry, dict) else None
        items.append(RawSource(str(url) if isinstance(url, str) else ""))
    return items


def parse_catalog(text: str) -> tuple[dict[str, Any], list[RawSource]]:
    """Bloco JSON único entre os marcadores; habilitadas ordenadas por prioridade."""
    if text.count(CATALOG_START) != 1 or text.count(CATALOG_END) != 1:
        raise InputError("O catálogo precisa de exatamente um par de marcadores RAG_SOURCE_CATALOG.")
    block = text.split(CATALOG_START, 1)[1].split(CATALOG_END, 1)[0].strip()
    if block.startswith("```"):
        lines = block.splitlines()
        if len(lines) < 2 or not lines[-1].strip().startswith("```"):
            raise InputError("Bloco JSON do catálogo malformado.")
        block = "\n".join(lines[1:-1])
    try:
        data = json.loads(block)
    except json.JSONDecodeError as exc:
        raise InputError(f"JSON do catálogo inválido: {exc}") from None
    if not isinstance(data, dict) or data.get("catalog_schema") != CATALOG_SCHEMA:
        raise InputError(f"catalog_schema precisa ser {CATALOG_SCHEMA}.")
    sources = data.get("sources")
    if not isinstance(sources, list) or len(sources) > MAX_SOURCES:
        raise InputError("Lista de fontes do catálogo ausente ou acima do limite.")
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    enabled: list[tuple[int, int, RawSource]] = []
    required = {"id": str, "title": str, "kind": str, "url": str, "priority": int, "enabled": bool}
    for index, entry in enumerate(sources):
        if not isinstance(entry, dict):
            raise InputError(f"Fonte {index} do catálogo não é um objeto.")
        for name, kind in required.items():
            value = entry.get(name)
            if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
                raise InputError(f"Fonte {entry.get('id', index)}: campo {name} ausente ou inválido.")
        if entry["kind"] not in {"article", "video"}:
            raise InputError(f"Fonte {entry['id']}: kind deve ser article ou video.")
        if entry["id"] in seen_ids:
            raise InputError(f"ID repetido no catálogo: {entry['id']}.")
        if entry["url"] in seen_urls:
            raise InputError(f"URL repetida no catálogo: {entry['url']}.")
        seen_ids.add(entry["id"])
        seen_urls.add(entry["url"])
        if entry["enabled"]:
            curation = {k: entry.get(k) for k in ("id", "title", "topic", "version", "notes", "kind")}
            include_comments = entry.get("include_comments")
            enabled.append(
                (
                    entry["priority"],
                    index,
                    RawSource(
                        entry["url"],
                        catalog_id=entry["id"],
                        curation=curation,
                        include_comments=include_comments if isinstance(include_comments, bool) else None,
                    ),
                )
            )
    enabled.sort(key=lambda item: (item[0], item[1]))
    return data, [item[2] for item in enabled]


def load_input(path: str | Path) -> list[RawSource]:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise InputError(f"Não foi possível ler {path}: {exc}") from None
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return from_text(text)
    if suffix == ".json":
        try:
            return from_manifest(json.loads(text))
        except json.JSONDecodeError as exc:
            raise InputError(f"Manifesto JSON inválido: {exc}") from None
    if suffix == ".md":
        return parse_catalog(text)[1]
    raise InputError("Use .txt (uma URL por linha), manifesto .json v1 ou catálogo .md.")
