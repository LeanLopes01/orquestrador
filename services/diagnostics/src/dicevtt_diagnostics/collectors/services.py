"""Disponibilidade do RAG (só health: não indexa nem gera) e do acesso MCP dos agentes."""

from __future__ import annotations

import json
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

from .base import CheckResult, Context, Finding


def _rag_health(port: int, token: str) -> dict | None:
    request = urllib.request.Request(f"http://127.0.0.1:{port}/v1/rag/health", headers={"X-Local-Token": token})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310 - loopback fixo
            return json.loads(response.read())
    except (OSError, ValueError, urllib.error.URLError):
        return None


def collect_rag(ctx: Context, check: CheckResult) -> None:
    link = ctx.config.rag
    if link is None:
        check.degrade("partial", "RAG não configurado (rag.config ausente ou ilegível).")
        return
    try:
        token = link.token_path.read_text(encoding="ascii").strip()
    except OSError:
        token = ""
    waited_until = min(time.monotonic() + ctx.config.rag_wait_seconds, ctx.deadline - 5)
    health = _rag_health(link.port, token)
    while (health is None or health.get("starting")) and time.monotonic() < waited_until:
        ctx.check_cancel()
        time.sleep(2)
        health = _rag_health(link.port, token)
    evidence = check.add_evidence("service", f"127.0.0.1:{link.port}/v1/rag/health",
                                  "sem resposta" if health is None else f"online, starting={health.get('starting')}")
    if health is None or health.get("starting"):
        check.data["rag"] = {"state": "offline" if health is None else "starting"}
        check.findings.append(Finding(
            rule="rag.unavailable", severity="low", state="confirmed", key="health", evidence=[evidence],
            summary="RAG local " + ("desligado" if health is None else "ainda iniciando") + " durante a coleta",
            recommendation="Agentes e o Jarvis ficam sem as fontes do projeto. Ligue com iniciar-tudo.cmd.",
        ))
        return
    index = health.get("index") or {}
    watcher = health.get("watcher") or {}
    check.data["rag"] = {"state": "online", "index_state": index.get("state"),
                         "code_pointers": index.get("code_pointers"), "document_chunks": index.get("document_chunks"),
                         "documents": index.get("documents"), "watcher": watcher.get("state"),
                         "model": (health.get("model") or {}).get("state")}
    if health.get("startup_error") or index.get("state") not in {"ready", None} or watcher.get("state") == "error":
        check.findings.append(Finding(
            rule="rag.degraded", severity="medium", state="confirmed", key="index", evidence=[evidence],
            summary=f"RAG online com problema: índice {index.get('state')}, watcher {watcher.get('state')}"
                    + (f", erro {health['startup_error']}" if health.get("startup_error") else ""),
            recommendation="Veja .local/rag/logs/service.log e reindexe pela tela RAG local.",
        ))


def collect_mcp(check: CheckResult, home: Path | None = None) -> None:
    home = home or Path.home()
    registered = {}
    try:
        claude = json.loads((home / ".claude.json").read_text(encoding="utf-8"))
        registered["claude_code"] = "dicevtt-rag" in (claude.get("mcpServers") or {})
    except (OSError, ValueError):
        registered["claude_code"] = None
    try:
        codex = tomllib.loads((home / ".codex" / "config.toml").read_text(encoding="utf-8"))
        registered["codex"] = "dicevtt-rag" in (codex.get("mcp_servers") or {})
    except (OSError, tomllib.TOMLDecodeError):
        registered["codex"] = None
    try:
        agy = json.loads((home / ".gemini" / "config" / "mcp_config.json").read_text(encoding="utf-8"))
        entry = (agy.get("mcpServers") or {}).get("dicevtt-rag")
        registered["antigravity"] = isinstance(entry, dict) and not entry.get("disabled", False)
    except (OSError, ValueError):
        registered["antigravity"] = None
    check.data["mcp"] = registered
    evidence = check.add_evidence(
        "file",
        "~/.claude.json, ~/.codex/config.toml, ~/.gemini/config/mcp_config.json",
        ", ".join(f"{k}: {v}" for k, v in registered.items()),
    )
    missing = [name for name, ok in registered.items() if ok is False]
    if missing:
        check.findings.append(Finding(
            rule="mcp.not-registered", severity="low", state="confirmed", key=",".join(missing), evidence=[evidence],
            summary="Servidor MCP dicevtt-rag não registrado em: " + ", ".join(missing),
            recommendation="Veja services/agent-rag/README.md.",
        ))


def collect(ctx: Context, check: CheckResult) -> None:
    collect_rag(ctx, check)
    collect_mcp(check)
    rag = check.data.get("rag") or {}
    mcp = check.data.get("mcp") or {}
    check.note = (f"RAG {rag.get('state', '?')}"
                  + (f" · {rag.get('code_pointers')} scripts, {rag.get('document_chunks')} trechos" if rag.get("state") == "online" else "")
                  + " · MCP " + ", ".join(f"{k} {'ok' if v else 'ausente' if v is False else '?'}" for k, v in mcp.items()))
