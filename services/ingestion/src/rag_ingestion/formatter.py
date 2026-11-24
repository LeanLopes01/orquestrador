"""Cabeçalho obrigatório + corpo Markdown (seção 8 do plano de ingestão).

Fonte/Tipo/Data de Extração abrem o arquivo; campos opcionais vêm antes do primeiro
`---` isolado. Linhas `Nome: valor` dividem no primeiro `:` (URLs têm dois-pontos).
"""

from __future__ import annotations

import hashlib
import re

from .models import ExtractedDocument, SourceSpec

TYPE_LABEL = {"article": "Artigo", "video": "Vídeo"}


class FormatError(ValueError):
    pass


def _value(text: str | None) -> str:
    if text is None:
        return ""
    if "\n" in text or "\r" in text:
        raise FormatError("Metadados não podem conter quebras de linha.")
    return text.strip()


def normalize_markdown(body: str) -> str:
    """LF, no máximo uma linha em branco e sem indentação herdada do HTML fora de blocos
    de código (o Trafilatura usa cercas ``` para código; espaços à esquerda de títulos e
    tabelas transformariam o texto em bloco de código no Markdown)."""
    lines = body.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    fenced = False
    blank = 0
    for line in lines:
        if line.lstrip().startswith("```"):
            fenced = not fenced
            out.append(line.rstrip())
            blank = 0
            continue
        if fenced:
            out.append(line)
            continue
        stripped = line.strip()
        if not stripped:
            blank += 1
            if blank > 1:
                continue
        else:
            blank = 0
        out.append(stripped)
    return "\n".join(out).strip("\n") + "\n"


def body_hash(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def build_markdown(
    document: ExtractedDocument,
    source: SourceSpec,
    *,
    extracted_at: str,
    acquired_at: str,
    final_url: str | None = None,
) -> str:
    header = [
        f"Fonte: {_value(source.original_url)}",
        f"Tipo: {TYPE_LABEL[source.kind]}",
        f"Data de Extração: {_value(extracted_at)}",
        f"Source ID: {source.source_id}",
        f"URL Canônica: {_value(source.canonical_url)}",
        f"Aquisição Original: {_value(acquired_at)}",
    ]
    if final_url and final_url != source.canonical_url:
        header.append(f"URL Final: {_value(final_url)}")
    if source.kind == "video":
        if document.language:
            header.append(f"Idioma: {_value(document.language)}")
        if document.caption:
            header.append(f"Legenda: {_value(document.caption)}")
    title = " ".join(document.title.split()) or "Documento sem título"
    body = normalize_markdown(document.body)
    # Evita título duplicado quando o extrator já abriu com o mesmo H1.
    first = body.split("\n", 1)[0]
    if re.match(r"^#\s+", first) and first.lstrip("# ").strip() == title:
        body = body.split("\n", 1)[1].lstrip("\n") if "\n" in body else ""
    return "\n".join(header) + "\n\n---\n\n# " + title + "\n\n" + body


def parse_header(text: str) -> tuple[dict[str, str], str]:
    """Inverso de build_markdown (usado nos testes de round-trip)."""
    text = text.lstrip("﻿")
    lines = text.split("\n")
    fields: dict[str, str] = {}
    for index, line in enumerate(lines):
        if line.strip() == "---":
            if not {"Fonte", "Tipo", "Data de Extração"} <= fields.keys():
                break
            return fields, "\n".join(lines[index + 1 :]).lstrip("\n")
        if not line.strip():
            continue
        name, sep, value = line.partition(":")
        if not sep:
            break
        fields[name.strip()] = value.strip()
    return {}, text
