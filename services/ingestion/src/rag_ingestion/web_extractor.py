"""Artigos: HTML do cache → Markdown com Trafilatura. Nunca acessa a rede."""

from __future__ import annotations

import re

from .models import ExtractedDocument, SourceFailure, Status

# Sinais de páginas que não são conteúdo (heurísticos; constam nos avisos).
_BLOCK_SIGNALS = re.compile(
    r"(captcha|verify you are human|are you a robot|enable javascript|please turn on javascript|"
    r"sign in to continue|faça login para continuar|access denied|just a moment\.\.\.)",
    re.IGNORECASE,
)


def extract_article(
    html: str, final_url: str | None, *, include_comments: bool = False, min_chars: int = 200
) -> ExtractedDocument:
    import trafilatura

    markdown = trafilatura.extract(
        html,
        url=final_url,
        output_format="markdown",
        include_links=True,
        include_tables=True,
        include_comments=include_comments,
        include_formatting=True,
        favor_recall=True,
        deduplicate=False,
    )
    text = (markdown or "").strip()
    plain = re.sub(r"[#>*_`\[\]()|\-]+", " ", text)
    if len(plain.split()) < 5 or len(plain) < min_chars:
        signal = _BLOCK_SIGNALS.search(html[:200_000])
        reason = "acesso bloqueado, CAPTCHA ou login" if signal else "conteúdo vazio ou gerado por JavaScript"
        raise SourceFailure(Status.SKIPPED, "content_unavailable", f"Sem conteúdo extraível ({reason}).")
    warnings: list[str] = []
    if _BLOCK_SIGNALS.search(text[:2000]):
        warnings.append("low_quality: o início do texto parece aviso de bloqueio/login (heurística).")
    if len(plain) < min_chars * 3:
        warnings.append("low_quality: texto curto após a extração; revise se a página foi preservada.")
    if "```" not in text and re.search(r"<pre|<code", html, re.IGNORECASE):
        warnings.append("code_blocks: a página tem blocos de código que podem não ter sido preservados.")
    title = None
    try:
        metadata = trafilatura.extract_metadata(html, default_url=final_url)
        title = getattr(metadata, "title", None) if metadata else None
    except Exception:  # metadados são opcionais; a extração principal já passou
        title = None
    if not title:
        heading = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        title = heading.group(1).strip() if heading else (final_url or "Documento sem título")
    return ExtractedDocument(title=" ".join(str(title).split())[:300], body=text, warnings=warnings)
