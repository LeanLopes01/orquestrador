"""Índices oficiais de documentação: baixados, guardados em cache e convertidos em entradas.

Formatos aceitos (todos conferidos em 22/10/2026):
  unity_pages   ScriptReference/docdata/index.js   `var pages = [[slug, título], ...]`
  unity_toc     Manual/docdata/toc.json            árvore {title, link, children}
  docfx_xrefmap Packages/<pkg>/xrefmap.yml          referências da API (somente tipos T:)
  html_links    sumário HTML (docfx toc.html, wiki Facepunch)

Os índices vêm de URLs fixas do TOML; as páginas descobertas seguem depois pelo
transporte protegido da ingestão, nunca por este módulo.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

from .config import CatalogSpec, DiscoveryConfig

MAX_INDEX_BYTES = 40 * 1024 * 1024
IDENTIFIER = re.compile(r"^[A-Z][A-Za-z0-9_]*$")
CODE_PATH = re.compile(r"^[A-Z]\w*(?:\.[A-Za-z_]\w*)*$")
_ANCHOR = re.compile(r"<a\s([^>]*)>(.*?)</a>", re.IGNORECASE | re.DOTALL)
_HREF = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
_TITLE = re.compile(r"""title\s*=\s*["']([^"']*)["']""", re.IGNORECASE)
_TAG = re.compile(r"<[^>]+>")

Fetcher = Callable[[str, str], str]


@dataclass(frozen=True)
class Entry:
    url: str
    title: str
    label: str  # texto usado na busca semântica (breadcrumb/nome completo)
    catalog: str
    symbol: str | None = None  # "Tilemap" ou "Physics2D.Raycast"
    namespaces: frozenset[str] | None = None  # None: qualquer namespace
    api: bool = False
    topic: bool = False


def _strip_fragment(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))


def _unity_namespaces(prefix: str) -> frozenset[str]:
    if not prefix:
        return frozenset({"UnityEngine", "UnityEditor"})
    if prefix.startswith(("UnityEngine", "UnityEditor", "Unity.")):
        return frozenset({prefix})
    return frozenset({f"UnityEngine.{prefix}", f"UnityEditor.{prefix}"})


def parse_unity_pages(text: str, spec: CatalogSpec) -> list[Entry]:
    start = text.index("[", text.index("var pages"))
    pages, _ = json.JSONDecoder().raw_decode(text[start:])
    entries = []
    for slug, title in pages:
        if not isinstance(slug, str) or not isinstance(title, str) or title.count(".") > 1:
            continue
        dotted = slug.replace("-", ".")
        if not dotted.endswith(title):
            continue
        prefix = dotted[: -len(title)].rstrip(".")
        head = title.split(".")[0]
        if not IDENTIFIER.match(head):
            continue
        entries.append(Entry(
            url=spec.base + slug + ".html", title=title, label=f"{prefix + '.' if prefix else ''}{title}",
            catalog=spec.id, symbol=title, namespaces=_unity_namespaces(prefix), api=spec.api, topic=spec.topics,
        ))
    return entries


def parse_unity_toc(text: str, spec: CatalogSpec) -> list[Entry]:
    entries: list[Entry] = []

    def walk(node: dict, crumbs: list[str]) -> None:
        for child in node.get("children") or []:
            title = str(child.get("title") or "").strip()
            link = child.get("link")
            path = crumbs + [title]
            if title and isinstance(link, str) and link and link != "null":
                entries.append(Entry(url=spec.base + link + ".html", title=title, label=" > ".join(path),
                                     catalog=spec.id, api=False, topic=spec.topics))
            walk(child, path)

    walk(json.loads(text), [])
    return entries


def parse_docfx_xrefmap(text: str, spec: CatalogSpec) -> list[Entry]:
    entries = []
    for block in text.split("\n- uid:")[1:]:
        fields = {}
        for line in block.splitlines()[1:]:
            key, _, value = line.strip().partition(": ")
            if key in {"name", "href", "commentId", "fullName"}:
                fields[key] = value.strip().strip("'\"")
        if not fields.get("commentId", "").startswith("T:") or "#" in fields.get("href", "#"):
            continue
        name = re.sub(r"<.*>$|`\d+$", "", fields.get("name", ""))
        full = fields.get("fullName", "")
        if not IDENTIFIER.match(name):
            continue
        namespace = full[: full.rfind("." + name)] if "." + name in full else ""
        entries.append(Entry(
            url=_strip_fragment(urljoin(spec.base, fields["href"])), title=name, label=full or name,
            catalog=spec.id, symbol=name, namespaces=frozenset({namespace}) if namespace else None,
            api=spec.api, topic=spec.topics,
        ))
    return entries


def parse_html_links(text: str, spec: CatalogSpec) -> list[Entry]:
    base = urlsplit(spec.base)
    prefix = spec.path_prefix or base.path
    seen: set[str] = set()
    entries = []
    for attrs, inner in _ANCHOR.findall(text):
        href = _HREF.search(attrs)
        if not href:
            continue
        url = _strip_fragment(urljoin(spec.index, html.unescape(href.group(1))))
        parts = urlsplit(url)
        if parts.netloc != base.netloc or not parts.path.startswith(prefix) or "~" in parts.path:
            continue
        if url in seen or url.rstrip("/") == spec.index.rstrip("/"):
            continue
        title_attr = _TITLE.search(attrs)
        title = html.unescape(title_attr.group(1) if title_attr and title_attr.group(1) else _TAG.sub("", inner))
        title = " ".join(title.split())
        if not title:
            continue
        seen.add(url)
        # Página de código quando o caminho é Tipo ou Escopo.Tipo e termina no texto do link:
        # Data.Lobby → Lobby em <namespace>.Data. "P2P Networking" (Sending_P2P_Messages) é guia.
        last = parts.path.rstrip("/").rsplit("/", 1)[-1]
        pieces = last.split(".")
        is_code = bool(CODE_PATH.match(last)) and pieces[-1] == title
        symbol = title if is_code else None
        scope = ".".join(([spec.namespace] if spec.namespace else []) + pieces[:-1])
        api = spec.api and is_code
        entries.append(Entry(
            url=url, title=title, label=title, catalog=spec.id, symbol=symbol,
            namespaces=frozenset({scope}) if scope else None,
            api=api, topic=spec.topics and not is_code,  # páginas de API ficam com a estratégia de código
        ))
    return entries


PARSERS = {
    "unity_pages": parse_unity_pages,
    "unity_toc": parse_unity_toc,
    "docfx_xrefmap": parse_docfx_xrefmap,
    "html_links": parse_html_links,
}


def http_fetch(url: str, user_agent: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read(MAX_INDEX_BYTES + 1)
    if len(body) > MAX_INDEX_BYTES:
        raise ValueError(f"índice acima de {MAX_INDEX_BYTES // (1024 * 1024)} MiB")
    return body.decode("utf-8", errors="replace")


def _cache_file(config: DiscoveryConfig, spec: CatalogSpec) -> Path:
    digest = hashlib.sha256(spec.index.encode()).hexdigest()[:12]
    return config.cache_root / "catalogs" / f"{spec.id}-{digest}.txt"


def load_catalog(config: DiscoveryConfig, spec: CatalogSpec, *, refresh: bool = False,
                 fetch: Fetcher = http_fetch) -> tuple[list[Entry], str | None]:
    """(entradas, aviso). Índice vencido que falha ao baixar usa o cache antigo."""
    path = _cache_file(config, spec)
    fresh = path.exists() and time.time() - path.stat().st_mtime < config.catalog_ttl_days * 86400
    warning = None
    if refresh or not fresh:
        try:
            text = fetch(spec.index, config.user_agent)
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(text, encoding="utf-8")
            os.replace(tmp, path)
        except Exception as exc:  # rede/HTTP/tamanho: segue com o cache, se houver
            if not path.exists():
                return [], f"{spec.id}: índice indisponível ({type(exc).__name__}: {exc})"
            warning = f"{spec.id}: usando cache antigo ({type(exc).__name__}: {exc})"
    try:
        return PARSERS[spec.kind](path.read_text(encoding="utf-8"), spec), warning
    except (ValueError, KeyError, TypeError) as exc:
        return [], f"{spec.id}: índice em formato inesperado ({type(exc).__name__}: {exc})"


def load_entries(config: DiscoveryConfig, *, refresh: bool = False,
                 fetch: Fetcher = http_fetch) -> tuple[list[Entry], list[str]]:
    entries: list[Entry] = []
    warnings: list[str] = []
    for spec in config.catalogs:
        items, warning = load_catalog(config, spec, refresh=refresh, fetch=fetch)
        entries.extend(items)
        if warning:
            warnings.append(warning)
    return entries, warnings
