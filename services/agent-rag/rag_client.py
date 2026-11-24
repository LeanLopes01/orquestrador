"""Cliente mínimo do unity_rag (127.0.0.1:8767) para agentes de código (Claude Code, Codex).

Só biblioteca padrão: roda com qualquer Python 3.10+, sem depender do .venv-rag.
O token vem de .local/rag/api-token (o mesmo que a ponte Vite injeta).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TOKEN_PATH = Path(os.environ.get("DICEVTT_RAG_TOKEN") or ROOT / ".local" / "rag" / "api-token")
BASE_URL = os.environ.get("DICEVTT_RAG_URL", "http://127.0.0.1:8767")
MAX_QUERY_CHARS = 2000  # [retrieval] max_query_chars do .local/rag.toml
OFFLINE_HINT = ("RAG local do DiceVTT desligado. Ligue com iniciar-tudo.cmd "
                "(D:\\Programação\\ProjetoLocais\\Orquestrador) ou iniciando o helper Jarvis Desktop.")


class RagUnavailable(RuntimeError):
    """Serviço desligado, iniciando ou recusando a requisição: a mensagem já é legível."""


def _request(method: str, path: str, body: dict[str, Any] | None = None, timeout: float = 30) -> dict[str, Any]:
    try:
        token = TOKEN_PATH.read_text(encoding="ascii").strip()
    except OSError:
        raise RagUnavailable(f"Token do RAG não encontrado em {TOKEN_PATH}. {OFFLINE_HINT}") from None
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(BASE_URL + path, data=data, method=method,
                                 headers={"X-Local-Token": token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            message = json.loads(exc.read().decode("utf-8")).get("message")
        except (ValueError, AttributeError):
            message = None
        raise RagUnavailable(f"RAG respondeu {exc.code}: {message or exc.reason}") from None
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        raise RagUnavailable(f"{OFFLINE_HINT} ({getattr(exc, 'reason', exc)})") from None


def health(timeout: float = 5) -> dict[str, Any]:
    return _request("GET", "/v1/rag/health", timeout=timeout)


def retrieve(query: str, text_limit: int = 20_000, timeout: float = 30) -> dict[str, Any]:
    query = " ".join(query.split())[:MAX_QUERY_CHARS]
    if not query:
        raise RagUnavailable("A consulta está vazia.")
    result = _request("POST", "/v1/rag/retrieve", {"query": query, "text_limit": text_limit}, timeout=timeout)
    if "sources" not in result:  # health ainda em "starting" responde sem o contrato completo
        raise RagUnavailable("RAG ainda iniciando (carregando embeddings). Tente de novo em alguns segundos.")
    return result


def start_index(scope: str) -> dict[str, Any]:
    return _request("POST", "/v1/rag/index-jobs", {"scope": scope})


def index_job(job_id: str) -> dict[str, Any]:
    return _request("GET", f"/v1/rag/index-jobs/{job_id}")


def describe(source: dict[str, Any]) -> str:
    """Cabeçalho de uma fonte: id, tipo, caminho, linhas e estado."""
    kind = "código" if source.get("kind") == "code_pointer" else "doc"
    where = source.get("relpath") or source.get("filepath") or "?"
    lines = source.get("lines")
    if lines:
        where += f":{lines[0]}-{lines[1]}"
    extra = [f"dist {source.get('distance', 0):.3f}"]
    if source.get("state") not in {None, "current", "snapshot"}:  # snapshot é o normal dos docs
        extra.append(source["state"])
    if source.get("section"):
        extra.append(f"seção {source['section']}")
    origin = (source.get("provenance") or {}).get("source_url")
    if origin:
        extra.append(f"origem {origin}")
    if source.get("kind") == "code_pointer" and source.get("filepath"):
        extra.append(source["filepath"])
    return f"[{source.get('id')}] {kind} · {where} ({'; '.join(extra)})"
