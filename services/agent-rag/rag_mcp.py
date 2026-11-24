"""Servidor MCP (stdio) do RAG do DiceVTT para Claude Code e Codex.

Ferramentas: rag_buscar (fontes atuais, sem geração), rag_status e rag_reindexar.
A geração com o AirLLM fica de fora de propósito: leva minutos no CPU e o próprio agente
responde melhor a partir das fontes. Protocolo: JSON-RPC 2.0, uma mensagem por linha.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rag_client  # noqa: E402

SERVER_INFO = {"name": "dicevtt-rag", "version": "0.1.0"}
PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
KINDS = {"tudo": None, "codigo": "code_pointer", "docs": "documentation"}
INSTRUCTIONS = (
    "RAG local do DiceVTT (Unity, C:\\ProjetoTablepRPG\\DiceVTT): scripts C# de Assets/Scripts lidos do disco "
    "na hora da consulta e documentação coletada (Unity, Netcode, Steamworks…). Use rag_buscar no começo de "
    "tarefas sobre o DiceVTT e sempre que precisar entender um script, classe ou sistema que ainda não leu; "
    "prefira consultas específicas (nome do .cs/classe, sistema, API). Cite os caminhos retornados."
)

TOOLS = [
    {
        "name": "rag_buscar",
        "description": (
            "Busca no RAG do DiceVTT os scripts C# e trechos de documentação mais relevantes para a consulta. "
            "Scripts vêm com o conteúdo atual do disco, caminho e hash; docs vêm com a origem. Leva menos de 1 s."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "consulta": {"type": "string", "description": "Pergunta ou termos (ex.: 'SteamLobbyManager cria lobby')."},
                "tipo": {"type": "string", "enum": list(KINDS), "default": "tudo",
                         "description": "Filtra fontes: codigo (.cs), docs (documentação) ou tudo."},
                "max_caracteres_por_fonte": {"type": "integer", "minimum": 200, "maximum": 60000, "default": 6000,
                                             "description": "Corta o texto de cada fonte (arquivos .cs vêm inteiros)."},
            },
            "required": ["consulta"],
        },
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "rag_status",
        "description": "Estado do RAG do DiceVTT: online, índice, watcher de scripts e modelo local.",
        "inputSchema": {"type": "object", "properties": {}},
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    },
    {
        "name": "rag_reindexar",
        "description": (
            "Reindexa o RAG (code = scripts C#, documents = documentacao_rag, all). O watcher já acompanha os "
            "scripts; use depois de ingerir documentação nova ou se a busca parecer desatualizada."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"escopo": {"type": "string", "enum": ["code", "documents", "all"], "default": "all"}},
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False},
    },
]


def search(args: dict[str, Any]) -> str:
    kind = KINDS.get(str(args.get("tipo") or "tudo"), None)
    limit = min(max(int(args.get("max_caracteres_por_fonte") or 6000), 200), 60_000)
    result = rag_client.retrieve(str(args.get("consulta") or ""), text_limit=limit)
    sources = [s for s in result["sources"] if kind is None or s.get("kind") == kind]
    parts = [f"Consulta: {result['query']} · {len(sources)} fonte(s) · {sum(result.get('timings_ms', {}).values())} ms"]
    for source in sources:
        text = source.get("text", "").strip()
        if source.get("text_truncated"):
            text += f"\n…(cortado em {limit} caracteres; aumente max_caracteres_por_fonte ou leia o arquivo)"
        header = f"{rag_client.describe(source)}\nhash {str(source.get('hash', ''))[:16]} · lido {source.get('read_at', '?')}"
        summary = (source.get("provenance") or {}).get("summary")
        if source.get("kind") == "code_pointer" and summary:
            header += f"\nResumo: {summary}"
        parts.append(f"{header}\n{text}")
    if result.get("warnings"):
        parts.append("Avisos: " + " | ".join(result["warnings"]))
    if not sources:
        parts.append("Nenhuma fonte encontrada. Tente outros termos (nome de classe, método ou sistema).")
    return "\n\n---\n\n".join(parts)


def status(_args: dict[str, Any]) -> str:
    return json.dumps(rag_client.health(), ensure_ascii=False, indent=1)


def reindex(args: dict[str, Any]) -> str:
    scope = str(args.get("escopo") or "all")
    job = rag_client.start_index(scope)
    job_id = job["job_id"]
    deadline = time.monotonic() + 90
    while job.get("state") in {"queued", "running"} and time.monotonic() < deadline:
        time.sleep(2)
        job = rag_client.index_job(job_id)
    if job.get("state") in {"queued", "running"}:
        return f"Reindexação {scope} ainda em andamento (job {job_id}). Consulte rag_status mais tarde."
    return json.dumps(job, ensure_ascii=False, indent=1)


HANDLERS = {"rag_buscar": search, "rag_status": status, "rag_reindexar": reindex}


def handle(message: dict[str, Any]) -> dict[str, Any] | None:
    method, params, msg_id = message.get("method"), message.get("params") or {}, message.get("id")
    if msg_id is None:  # notificação (ex.: notifications/initialized)
        return None
    if method == "initialize":
        requested = params.get("protocolVersion")
        result = {"protocolVersion": requested if requested in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
                  "capabilities": {"tools": {"listChanged": False}}, "serverInfo": SERVER_INFO,
                  "instructions": INSTRUCTIONS}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        handler = HANDLERS.get(params.get("name"))
        if handler is None:
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32602, "message": f"Ferramenta desconhecida: {params.get('name')}"}}
        try:
            result = {"content": [{"type": "text", "text": handler(params.get("arguments") or {})}]}
        except rag_client.RagUnavailable as exc:
            result = {"content": [{"type": "text", "text": str(exc)}], "isError": True}
        except Exception as exc:
            result = {"content": [{"type": "text", "text": f"{type(exc).__name__}: {exc}"}], "isError": True}
    else:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Método não suportado: {method}"}}
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def main() -> int:
    out = sys.stdout.buffer
    for line in sys.stdin.buffer:
        if not line.strip():
            continue
        try:
            message = json.loads(line.decode("utf-8"))
        except ValueError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "JSON inválido."}}
        else:
            reply = handle(message) if isinstance(message, dict) else None
        if reply is not None:
            out.write(json.dumps(reply, ensure_ascii=False).encode("utf-8") + b"\n")
            out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
