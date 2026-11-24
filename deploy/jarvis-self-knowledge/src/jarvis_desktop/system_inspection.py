"""Fixed read-only inventory. Never return config values, credentials or commands."""

from __future__ import annotations

import asyncio
import json
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import aiohttp

from .rag_service import orchestrator_root


def registrations(home: Path) -> dict:
    result = {}
    for client, path in (
        ("claude_code", home / ".claude.json"),
        ("codex", home / ".codex/config.toml"),
    ):
        try:
            if path.stat().st_size > 2_000_000:
                result[client] = {"state": "too_large", "path": str(path)}
                continue
            text = path.read_text(encoding="utf-8-sig")
            data = json.loads(text) if client == "claude_code" else tomllib.loads(text)
            servers = data.get(
                "mcpServers" if client == "claude_code" else "mcp_servers", {}
            )
            result[client] = {
                "state": "configured",
                "path": str(path),
                "servers": [
                    {
                        "name": str(name)[:100],
                        "enabled": cfg.get("enabled", True) is not False,
                    }
                    for name, cfg in list(servers.items())[:50]
                    if isinstance(cfg, dict)
                ],
                "scope": "user-level only; project/plugin configuration and live MCP handshakes not checked",
            }
        except FileNotFoundError:
            result[client] = {"state": "not_found", "path": str(path)}
        except (OSError, ValueError, TypeError, AttributeError):
            result[client] = {"state": "unreadable", "path": str(path)}
    return result


async def inspect_system(params: dict) -> dict:
    root = orchestrator_root()

    async def health(name, port, route, token_file, expected):
        try:
            token = (root / token_file).read_text(encoding="ascii").strip()
            async with (
                aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as client,
                client.get(
                    f"http://127.0.0.1:{port}{route}",
                    headers={"X-Local-Token": token},
                    allow_redirects=False,
                ) as response,
            ):
                data = await response.json()
                if response.status != 200 or data.get("service") != expected:
                    return name, {"state": "unavailable"}
                return name, {
                    "state": "responding",
                    "version": data.get("version"),
                    "capabilities": data.get("capabilities", {}),
                }
        except (OSError, ValueError, aiohttp.ClientError, TimeoutError):
            return name, {"state": "unavailable"}

    services = dict(
        await asyncio.gather(
            health(
                "audits",
                8768,
                "/v1/diagnostics/health",
                ".local/audits/api-token",
                "dicevtt-diagnostics",
            ),
        )
    )
    return {
        "observed_at": datetime.now(UTC).isoformat(),
        "orchestrator_root": str(root),
        "mcp": await asyncio.to_thread(registrations, Path.home()),
        "services": services,
        "limits": "Registrations are not connection tests. No MCP process was started; no arbitrary file read or shell command.",
    }
