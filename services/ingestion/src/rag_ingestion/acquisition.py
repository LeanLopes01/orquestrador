"""Transporte HTTP controlado (stdlib) e cache de aquisição versionado.

Cada conexão usa o IP validado na resolução DNS (sem nova resolução entre a checagem
e o connect), com SNI/Host do domínio original. Redirecionamentos são seguidos
manualmente e revalidados um a um.
"""

from __future__ import annotations

import email.utils
import hashlib
import http.client
import ipaddress
import json
import os
import shutil
import socket
import ssl
import time
import zlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

from .config import NetworkPolicy
from .models import AcquiredSource, RetryableFailure, SourceFailure, Status
from .urls import YOUTUBE_HOSTS, UrlError, normalize

CACHE_SCHEMA = 1
HTML_TYPES = {"text/html", "application/xhtml+xml"}


class RedirectedToVideo(Exception):
    """Um artigo redirecionou para o YouTube: o pipeline troca para o adaptador de vídeo."""

    def __init__(self, url: str) -> None:
        super().__init__(url)
        self.url = url


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


@dataclass
class HttpResponse:
    status: int
    final_url: str
    mime: str
    charset: str | None
    body: bytes
    acquired_at: str
    redirects: list[str]


def _is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def resolve_public(host: str, port: int) -> str:
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        if exc.errno in {socket.EAI_NONAME, getattr(socket, "EAI_NODATA", -5)}:
            raise SourceFailure(Status.FAILED, "dns_not_found", "Domínio não encontrado.") from None
        raise RetryableFailure("transient_network", "Falha temporária de DNS.") from None
    addresses = [info[4][0] for info in infos]
    if not addresses or not all(_is_public(a) for a in addresses):
        raise SourceFailure(
            Status.FAILED, "blocked_destination", "O domínio resolve para um endereço não público."
        )
    return addresses[0]


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host: str, ip: str, port: int, timeout: float) -> None:
        super().__init__(host, port, timeout=timeout)
        self._ip = ip

    def connect(self) -> None:
        self.sock = socket.create_connection((self._ip, self.port), self.timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, ip: str, port: int, timeout: float, context: ssl.SSLContext) -> None:
        super().__init__(host, port, timeout=timeout, context=context)
        self._ip = ip
        self._ctx = context

    def connect(self) -> None:
        sock = socket.create_connection((self._ip, self.port), self.timeout)
        self.sock = self._ctx.wrap_socket(sock, server_hostname=self.host)


def _read_limited(response: http.client.HTTPResponse, limit: int) -> bytes:
    encoding = (response.getheader("Content-Encoding") or "identity").lower().strip()
    declared = response.getheader("Content-Length")
    if encoding == "identity" and declared and declared.isdigit() and int(declared) > limit:
        raise SourceFailure(Status.SKIPPED, "unsupported_content", "Página maior que o limite configurado.")
    if encoding in {"gzip", "x-gzip"}:
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    elif encoding == "deflate":
        decoder = zlib.decompressobj()
    elif encoding == "identity":
        decoder = None
    else:
        raise SourceFailure(Status.SKIPPED, "unsupported_content", f"Codificação {encoding} não suportada.")
    out = bytearray()
    while True:
        chunk = response.read(65536)
        if not chunk:
            break
        out.extend(decoder.decompress(chunk, limit + 1 - len(out)) if decoder else chunk)
        if len(out) > limit:
            raise SourceFailure(Status.SKIPPED, "unsupported_content", "Página maior que o limite configurado.")
    if decoder:
        out.extend(decoder.flush())
        if len(out) > limit:
            raise SourceFailure(Status.SKIPPED, "unsupported_content", "Página maior que o limite configurado.")
    return bytes(out)


def _retry_after(value: str | None) -> float | None:
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        parsed = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max(0.0, (parsed - datetime.now(timezone.utc)).total_seconds())


def fetch_web_page(url: str, policy: NetworkPolicy, *, deadline: float | None = None) -> HttpResponse:
    """GET com limites de tempo/tamanho/redirects; erros mapeados em códigos estáveis."""
    context = ssl.create_default_context()
    current = url
    redirects: list[str] = []
    for _ in range(policy.max_redirects + 1):
        if deadline is not None and time.monotonic() > deadline:
            raise RetryableFailure("transient_network", "Prazo da fonte esgotado.")
        try:
            current, host, _path = normalize(current)
        except UrlError as exc:
            raise SourceFailure(Status.FAILED, exc.reason, str(exc)) from None
        if redirects and host in YOUTUBE_HOSTS:
            raise RedirectedToVideo(current)
        parts = urlsplit(current)
        port = parts.port or (443 if parts.scheme == "https" else 80)
        ip = resolve_public(host, port)
        timeout = policy.timeout_seconds
        if deadline is not None:
            timeout = max(1.0, min(timeout, deadline - time.monotonic()))
        conn: http.client.HTTPConnection = (
            _PinnedHTTPSConnection(host, ip, port, timeout, context)
            if parts.scheme == "https"
            else _PinnedHTTPConnection(host, ip, port, timeout)
        )
        target = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
        try:
            conn.request(
                "GET",
                target,
                headers={
                    "User-Agent": policy.user_agent,
                    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1",
                    "Accept-Encoding": "gzip, deflate",
                    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
                },
            )
            response = conn.getresponse()
            status = response.status
            if status in {301, 302, 303, 307, 308}:
                location = response.getheader("Location")
                response.close()
                if not location:
                    raise SourceFailure(Status.FAILED, "bad_redirect", "Redirecionamento sem destino.")
                redirects.append(current)
                current = urljoin(current, location)
                continue
            if status in {401, 403}:
                raise SourceFailure(Status.FAILED, "access_blocked", f"Acesso bloqueado (HTTP {status}).")
            if status in {404, 410}:
                raise SourceFailure(Status.FAILED, "not_found", f"Página não encontrada (HTTP {status}).")
            if status == 429:
                raise RetryableFailure(
                    "rate_limited", "Servidor pediu para aguardar (HTTP 429).",
                    _retry_after(response.getheader("Retry-After")),
                )
            if status >= 500:
                raise RetryableFailure("transient_network", f"Erro temporário do servidor (HTTP {status}).")
            if status != 200:
                raise SourceFailure(Status.FAILED, "http_error", f"Resposta HTTP {status} inesperada.")
            content_type = response.getheader("Content-Type") or ""
            # Alguns servidores repetem o cabeçalho ("text/html,text/html").
            mime = content_type.split(";")[0].split(",")[0].strip().lower()
            charset = None
            for piece in content_type.split(";")[1:]:
                key, _, value = piece.strip().partition("=")
                if key.lower() == "charset":
                    charset = value.strip("\"' ") or None
            if mime and mime not in HTML_TYPES:
                raise SourceFailure(Status.SKIPPED, "unsupported_content", f"Tipo {mime} fora do escopo.")
            body = _read_limited(response, policy.max_html_bytes)
            return HttpResponse(status, current, mime or "text/html", charset, body, now_iso(), redirects)
        except ssl.SSLCertVerificationError:
            raise SourceFailure(Status.FAILED, "tls_error", "Certificado TLS inválido.") from None
        except ssl.SSLError as exc:
            raise SourceFailure(Status.FAILED, "tls_error", f"Falha TLS: {exc.reason}") from None
        except (TimeoutError, socket.timeout):
            raise RetryableFailure("transient_network", "Tempo de conexão esgotado.") from None
        except (ConnectionError, http.client.HTTPException, OSError) as exc:
            raise RetryableFailure("transient_network", f"Falha de rede: {type(exc).__name__}.") from None
        finally:
            conn.close()
    raise SourceFailure(Status.FAILED, "too_many_redirects", "Redirecionamentos acima do limite.")


# Cache -----------------------------------------------------------------------------


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_to_cache(
    cache_root: Path, source_id: str, kind: str, body: bytes, meta: dict[str, Any]
) -> AcquiredSource:
    """Grava a revisão num diretório temporário e o publica com rename atômico."""
    digest = _sha256(body)
    acquired_at = meta["acquired_at"]
    revision = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + digest[:8]
    base = cache_root / source_id
    base.mkdir(parents=True, exist_ok=True)
    tmp = base / f".tmp-{revision}"
    tmp.mkdir()
    name = "body.html" if kind == "article" else "transcript.json"
    try:
        (tmp / name).write_bytes(body)
        full = {**meta, "schema_version": CACHE_SCHEMA, "source_id": source_id, "kind": kind,
                "revision": revision, "body": name, "sha256": digest, "bytes": len(body)}
        (tmp / "meta.json").write_text(json.dumps(full, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, base / revision)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return AcquiredSource(source_id, kind, revision, acquired_at, meta.get("final_url"),
                          str(base / revision / name), digest, full)


def load_cached_source(source_id: str, cache_root: Path) -> AcquiredSource | None:
    """Revisão finalizada mais recente com hash íntegro; None se ausente/corrompida."""
    base = cache_root / source_id
    if not base.is_dir():
        return None
    for revision_dir in sorted((p for p in base.iterdir() if p.is_dir() and not p.name.startswith(".")), reverse=True):
        try:
            meta = json.loads((revision_dir / "meta.json").read_text(encoding="utf-8"))
            if meta.get("schema_version") != CACHE_SCHEMA or meta.get("source_id") != source_id:
                continue
            body_path = revision_dir / str(meta["body"])
            if _sha256(body_path.read_bytes()) != meta["sha256"]:
                continue
            return AcquiredSource(source_id, meta["kind"], meta["revision"], meta["acquired_at"],
                                  meta.get("final_url"), str(body_path), meta["sha256"], meta)
        except (OSError, ValueError, KeyError):
            continue
    return None


def prune_cache(cache_root: Path, keep_per_source: int = 3) -> int:
    """Limpeza explícita de revisões antigas; nunca toca nos documentos finais."""
    removed = 0
    if not cache_root.is_dir():
        return 0
    for source_dir in cache_root.iterdir():
        if not source_dir.is_dir():
            continue
        revisions = sorted((p for p in source_dir.iterdir() if p.is_dir()), reverse=True)
        for old in revisions[keep_per_source:]:
            shutil.rmtree(old, ignore_errors=True)
            removed += 1
    return removed


def clean_temporaries(cache_root: Path) -> None:
    if not cache_root.is_dir():
        return
    for source_dir in cache_root.iterdir():
        if source_dir.is_dir():
            for tmp in source_dir.glob(".tmp-*"):
                shutil.rmtree(tmp, ignore_errors=True)


def decode_html(body: bytes, charset: str | None) -> str:
    for candidate in (charset, "utf-8"):
        if not candidate:
            continue
        try:
            return body.decode(candidate)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", errors="replace")
