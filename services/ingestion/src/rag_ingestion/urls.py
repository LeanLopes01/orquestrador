"""Validação, normalização e classificação de URLs (espelha src/ingestion.ts).

O servidor repete toda a validação: kind, canonical_url e video_id enviados pela UI
não são confiáveis. A checagem de DNS/IP públicos acontece no transporte
(acquisition.py), vinculada à conexão.
"""

from __future__ import annotations

import hashlib
import ipaddress
import re
from urllib.parse import parse_qs, quote, urlsplit, urlunsplit

from .models import SourceSpec

MAX_URL_LENGTH = 4096
YOUTUBE_HOSTS = {
    "youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com",
    "youtube-nocookie.com", "www.youtube-nocookie.com", "youtu.be", "www.youtu.be",
}
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
DEFAULT_PORTS = {"http": 80, "https": 443}
_PATH_SAFE = "/%:@!$&'()*+,;=-._~"
_QUERY_SAFE = _PATH_SAFE + "?"


class UrlError(ValueError):
    def __init__(self, message: str, reason: str = "invalid_url") -> None:
        super().__init__(message)
        self.reason = reason


def source_id_for(canonical_url: str) -> str:
    return hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()


def _host(raw_host: str) -> str:
    host = raw_host.rstrip(".").lower()
    try:
        return host.encode("idna").decode("ascii")
    except UnicodeError:
        raise UrlError("Domínio inválido.") from None


def _public_host_syntax(host: str) -> None:
    if not host or host == "localhost" or host.endswith((".localhost", ".local")) or "." not in host:
        raise UrlError("Use um domínio público de documentação ou YouTube.", "blocked_destination")
    try:
        ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return
    raise UrlError("Use um domínio público de documentação ou YouTube.", "blocked_destination")


def normalize(raw: str) -> tuple[str, str, str]:
    """(url normalizada sem fragmento, host, caminho) ou UrlError."""
    original = raw.strip()
    if len(original) > MAX_URL_LENGTH:
        raise UrlError("URL muito longa (máximo de 4.096 caracteres).")
    if any(ch in original for ch in "\r\n\t"):
        raise UrlError("A URL não pode conter quebras de linha.")
    try:
        parts = urlsplit(original)
        port = parts.port
    except ValueError:
        raise UrlError("Informe uma URL completa com https:// ou http://.") from None
    scheme = parts.scheme.lower()
    if scheme not in DEFAULT_PORTS:
        raise UrlError("Somente links HTTP ou HTTPS são aceitos.")
    if parts.username or parts.password:
        raise UrlError("Remova usuário e senha da URL.")
    if not parts.hostname:
        raise UrlError("Informe uma URL completa com https:// ou http://.")
    host = _host(parts.hostname)
    _public_host_syntax(host)
    netloc = host if port in (None, DEFAULT_PORTS[scheme]) else f"{host}:{port}"
    path = quote(parts.path or "/", safe=_PATH_SAFE)
    query = quote(parts.query, safe=_QUERY_SAFE)
    return urlunsplit((scheme, netloc, path, query, "")), host, path


def classify(raw: str) -> SourceSpec:
    original = raw.strip()
    url, host, path = normalize(original)
    if host in YOUTUBE_HOSTS:
        parts = [p for p in path.split("/") if p]
        query = parse_qs(urlsplit(url).query)
        if host.endswith("youtu.be"):
            video_id = parts[0] if len(parts) == 1 else ""
        elif path == "/watch":
            video_id = (query.get("v") or [""])[0]
        elif len(parts) == 2 and parts[0] in {"shorts", "embed", "live"}:
            video_id = parts[1]
        else:
            video_id = ""
        if not VIDEO_ID.match(video_id):
            raise UrlError("Use o link de um vídeo; canais e playlists não são aceitos.")
        canonical = f"https://www.youtube.com/watch?v={video_id}"
        return SourceSpec("video", original, canonical, source_id_for(canonical), video_id)
    return SourceSpec("article", original, url, source_id_for(url))


def redact(url: str) -> str:
    """Representação para logs: sem query (pode conter tokens)."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return "<url inválida>"
    return urlunsplit((parts.scheme, parts.hostname or "", parts.path, "…" if parts.query else "", ""))
