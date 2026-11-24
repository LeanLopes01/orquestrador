import json

import pytest
from src.desktop_link import DesktopLinkError
from src.jarvis_desktop.system_inspection import registrations
from src.system_knowledge import SystemKnowledgeTools


class Link:
    online = True
    calls = None

    async def status(self):
        return {
            "online": self.online,
            "capabilities": ["rag.health", "orchestrator.runtime", "system.inspect"],
        }

    async def call(self, action, params, timeout):
        self.calls.append(action)
        if action == "rag.health":
            raise DesktopLinkError("private diagnostic must not leak")
        return {"online": True}


@pytest.mark.asyncio
async def test_live_status_partial_failure_and_reconnection():
    link = Link()
    link.calls = []
    tools = SystemKnowledgeTools(link)
    link.online = False
    first = await tools.inspect()
    assert first["desktop"]["online"] is False
    assert not link.calls
    link.online = True
    second = await tools.inspect()
    assert second["probes"]["rag.health"]["state"] == "unavailable"
    assert second["probes"]["orchestrator.runtime"]["online"]
    assert set(link.calls) == {"rag.health", "orchestrator.runtime", "system.inspect"}
    assert "private diagnostic" not in json.dumps(second)


@pytest.mark.asyncio
async def test_no_bridge_keeps_architecture_and_paths():
    result = await SystemKnowledgeTools(None).inspect()
    assert result["desktop"]["state"] == "bridge_not_configured"
    assert result["source_map"]["rag_mcp"].endswith("rag_mcp.py")
    assert "not those MCP clients" in result["architecture"]["mcp"]


def test_registration_inventory_never_returns_config_secrets(tmp_path):
    (tmp_path / ".claude.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "dicevtt-rag": {
                        "command": "secret-command",
                        "env": {"TOKEN": "do-not-leak"},
                    },
                    "bad": "malformed",
                },
                "projects": {"private-project": "private"},
            }
        )
    )
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".codex/config.toml").write_text(
        '[mcp_servers.disabled]\nenabled=false\nurl="https://secret.example/token"'
    )
    result = registrations(tmp_path)
    assert result["claude_code"]["servers"] == [
        {"name": "dicevtt-rag", "enabled": True}
    ]
    assert result["codex"]["servers"] == [{"name": "disabled", "enabled": False}]
    assert all(
        secret not in json.dumps(result)
        for secret in (
            "do-not-leak",
            "secret-command",
            "secret.example",
            "private-project",
        )
    )
    (tmp_path / ".claude.json").write_text("broken")
    assert registrations(tmp_path)["claude_code"]["state"] == "unreadable"


def test_assistant_always_has_self_inspection_and_dynamic_rag(monkeypatch):
    from src.agent import Assistant
    from src.project_knowledge import ProjectKnowledgeTools

    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    assistant = Assistant()
    assert "inspect_jarvis_system" in {t.id for t in assistant.tools}
    assert "inspect_jarvis_system" in assistant.system_knowledge.session_tools
    assert "ALWAYS call inspect_jarvis_system" in assistant.instructions
    assert "{system_knowledge_instructions}" not in assistant.instructions
    # Startup snapshot offline must not permanently hide retrieval.
    assert ProjectKnowledgeTools(Link(), False).tools
