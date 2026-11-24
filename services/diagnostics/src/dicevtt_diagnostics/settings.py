"""Preferências da rotina, no disco (o CMD e a UI leem a mesma fonte).

Versionadas por `revision`: um PUT com revisão antiga é recusado em vez de sobrescrever
silenciosamente. Gravação atômica (tmp + os.replace).
"""

from __future__ import annotations

import json
import os
import re
import threading
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

PROFILES = ("startup-light", "full-audit")
AI_PROVIDERS = ("local-rag", "claude-code")  # local-rag: nada sai do PC
_WORKFLOW_PATH = re.compile(r"^/workflow/[A-Za-z0-9_-]+/?$")


class SettingsError(ValueError):
    pass


class RevisionConflict(Exception):
    def __init__(self, current: AuditSettings) -> None:
        super().__init__("As preferências mudaram desde a leitura.")
        self.current = current


@dataclass(frozen=True)
class AuditSettings:
    revision: int = 0
    on_startup: bool = True
    profile: str = "startup-light"
    sync_to_server: bool = False
    investigate_with_ai: bool = False
    workflow_url: str = ""
    ai_provider: str = "local-rag"
    allow_code_to_provider: bool = False  # autorização explícita para enviar trechos de código a um provedor
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"version": 1, **asdict(self)}


def safe_workflow_url(value: str) -> str:
    """Mesma regra da UI: só a URL do editor n8n, sem credenciais, query ou fragmento."""
    value = value.strip()
    if not value:
        return ""
    parts = urlsplit(value)
    if (parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password
            or parts.query or parts.fragment or not _WORKFLOW_PATH.match(parts.path)):
        raise SettingsError("workflow_url precisa ser http(s)://host/workflow/ID, sem credenciais ou parâmetros.")
    return value


def validate(data: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key in ("on_startup", "sync_to_server", "investigate_with_ai"):
        if not isinstance(data.get(key), bool):
            raise SettingsError(f"{key} precisa ser true ou false.")
        clean[key] = data[key]
    if data.get("profile") not in PROFILES:
        raise SettingsError(f"profile deve ser um de {', '.join(PROFILES)}.")
    clean["profile"] = data["profile"]
    if not isinstance(data.get("workflow_url", ""), str) or len(data.get("workflow_url", "")) > 2048:
        raise SettingsError("workflow_url inválida.")
    clean["workflow_url"] = safe_workflow_url(data.get("workflow_url", ""))
    # Campos da investigação por IA: ausentes em preferências antigas, com padrão seguro.
    clean["ai_provider"] = data.get("ai_provider", "local-rag")
    if clean["ai_provider"] not in AI_PROVIDERS:
        raise SettingsError(f"ai_provider deve ser um de {', '.join(AI_PROVIDERS)}.")
    clean["allow_code_to_provider"] = data.get("allow_code_to_provider", False)
    if not isinstance(clean["allow_code_to_provider"], bool):
        raise SettingsError("allow_code_to_provider precisa ser true ou false.")
    if clean["ai_provider"] == "claude-code" and clean["investigate_with_ai"] and not clean["allow_code_to_provider"]:
        raise SettingsError("Investigar com o Claude Code envia trechos do código à Anthropic: "
                            "marque a autorização (allow_code_to_provider) ou use o provedor local.")
    return clean


class SettingsStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def load(self) -> AuditSettings:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return AuditSettings()
        except (OSError, ValueError) as exc:
            raise SettingsError(f"Preferências ilegíveis em {self.path}: {exc}") from None
        if not isinstance(data, dict) or data.get("version") != 1:
            raise SettingsError(f"Preferências com versão desconhecida em {self.path}.")
        return AuditSettings(revision=int(data.get("revision", 0)), updated_at=data.get("updated_at"),
                             **validate(data))

    def save(self, data: dict[str, Any], expected_revision: int) -> AuditSettings:
        clean = validate(data)
        with self._lock:
            current = self.load()
            if expected_revision != current.revision:
                raise RevisionConflict(current)
            updated = AuditSettings(revision=current.revision + 1,
                                    updated_at=datetime.now(UTC).isoformat(timespec="seconds"), **clean)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(updated.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, self.path)
            return updated
