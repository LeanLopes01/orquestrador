"""Checks por perfil. A ordem importa: unity alimenta o frescor dos logs e a auditoria completa."""

from __future__ import annotations

from collections.abc import Callable
from typing import NamedTuple

from . import full, logs, services, unity, vcs
from .base import CheckResult, Context

Collector = Callable[[Context, CheckResult], None]


class PlannedCheck(NamedTuple):
    id: str
    name: str
    collect: Collector | None
    budget: str  # "light" (prazo curto) ou "full" (prazo do perfil completo)
    skip_reason: str = ""  # sem coletor: registrado como não executado, com o motivo


LIGHT: list[PlannedCheck] = [
    PlannedCheck("vcs", "Controle de versão", vcs.collect, "light"),
    PlannedCheck("unity", "Unity, pacotes e scripts", unity.collect, "light"),
    PlannedCheck("logs", "Logs do Editor e do build", logs.collect, "light"),
    PlannedCheck("services", "RAG e acesso MCP", services.collect, "light"),
]


def plan(profile: str, full_configured: bool = True) -> list[PlannedCheck]:
    if profile != "full-audit":
        return list(LIGHT)
    if not full_configured:
        return LIGHT + [PlannedCheck(cid, name, None, "full", "Perfil completo não configurado: falta a seção "
                                     "[full] em .local/diagnostics.toml.") for cid, name, _ in full.CHECKS]
    return LIGHT + [PlannedCheck(cid, name, collect, "full") for cid, name, collect in full.CHECKS]
