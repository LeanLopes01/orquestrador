"""Contratos dos coletores e utilitários comuns.

Status de um check descreve a COLETA (collected/partial/error/skipped); a gravidade fica nos
achados. "Coletado sem achados" nunca é a mesma coisa que "não executado".
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from ..config import DiagnosticsConfig

TZ = ZoneInfo("America/Sao_Paulo")

CHECK_STATUSES = ("collected", "partial", "error", "skipped")
SEVERITIES = ("high", "medium", "low", "info")
FINDING_STATES = ("suspected", "confirmed")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # o helper roda sob pythonw

_SECRETS = [
    (re.compile(r"(?i)(authorization:\s*bearer\s+)[^\s\"']+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)\b(token|api[_-]?key|secret|password|passwd|pwd|access[_-]?key)(\s*[=:]\s*)[^\s\"',;]+"),
     r"\1\2[REDACTED]"),
    (re.compile(r"\b(sk|ghp|gho|xox[bap])[-_][A-Za-z0-9_-]{16,}"), "[REDACTED]"),
    (re.compile(r"(?i)([?&](?:key|token|sig|signature|auth)=)[^&\s\"']+"), r"\1[REDACTED]"),
]  # GUIDs da Unity (32 hex) ficam: são evidência, não segredo


def redact(text: str) -> str:
    for pattern, replacement in _SECRETS:
        text = pattern.sub(replacement, text)
    return text


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def local_time(value: str | float | None) -> str:
    """Datas exibidas ao usuário: America/Sao_Paulo. O JSON guarda UTC."""
    if value is None or value == "":
        return "—"
    try:
        moment = datetime.fromtimestamp(value, UTC) if isinstance(value, float) else datetime.fromisoformat(value)
    except ValueError:
        return str(value)
    return moment.astimezone(TZ).strftime("%d/%m/%Y %H:%M:%S")


def iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat(timespec="seconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class Evidence:
    id: str
    kind: str  # file | log_excerpt | command | service
    source: str
    detail: str = ""
    sha256: str | None = None
    observed_at: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Finding:
    rule: str
    severity: str
    state: str
    summary: str
    key: str  # parte estável da identidade (path normalizado, código, assinatura) — nunca a linha
    file: str | None = None
    line: int | None = None
    evidence: list[str] = field(default_factory=list)
    recommendation: str = ""
    origin: str = "collector"
    occurrences: int = 1

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(f"{self.rule}|{self.key}".lower().encode("utf-8")).hexdigest()[:24]

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "fingerprint": self.fingerprint}


@dataclass
class CheckResult:
    id: str
    name: str
    status: str = "collected"
    note: str = ""
    started_at: str = ""
    duration_ms: int = 0
    data: dict[str, Any] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)  # o que não pôde ser coletado, em texto

    def degrade(self, status: str, note: str) -> None:
        """Mantém o pior estado de coleta (collected < partial < error) e acumula a explicação."""
        order = {"collected": 0, "partial": 1, "error": 2}
        if order.get(status, 0) > order.get(self.status, 0):
            self.status = status
        self.problems.append(note)

    def add_evidence(self, kind: str, source: str, detail: str = "", **kw: Any) -> str:
        evidence_id = f"{self.id}-E{len(self.evidence) + 1}"
        self.evidence.append(Evidence(evidence_id, kind, source, detail, **kw))
        return evidence_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "status": self.status, "note": self.note, "problems": self.problems,
            "started_at": self.started_at, "duration_ms": self.duration_ms, "data": self.data,
            "evidence": [asdict(e) for e in self.evidence],
            "findings": [f.fingerprint for f in self.findings],
        }


class Cancelled(Exception):
    pass


@dataclass
class Context:
    """O que cada coletor recebe: configuração, prazo e sinal de cancelamento."""

    config: DiagnosticsConfig
    cancel: threading.Event
    deadline: float  # time.monotonic()
    run_dir: Path
    shared: dict[str, Any] = field(default_factory=dict)  # fatos de um check usados por outro
    cleanups: list[Callable[[], None]] = field(default_factory=list)  # rodam mesmo com cancelamento
    full_deadline: float = 0.0  # time.monotonic() do fim do perfil completo

    def remaining(self) -> float:
        return self.full_deadline - time.monotonic()

    def check_cancel(self) -> None:
        if self.cancel.is_set():
            raise Cancelled()


@dataclass
class CommandResult:
    code: int | None
    stdout: str
    stderr: str
    timed_out: bool = False


def run_command(args: list[str], cwd: Path, timeout: float, ctx: Context | None = None) -> CommandResult:
    """Subprocesso com lista de argumentos, sem shell, sem janela e com timeout real."""
    try:
        process = subprocess.Popen(args, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   stdin=subprocess.DEVNULL, creationflags=NO_WINDOW,
                                   env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"})
    except OSError as exc:
        return CommandResult(None, "", f"{type(exc).__name__}: {exc}")
    try:
        out, err = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        out, err = process.communicate()
        return CommandResult(None, out.decode("utf-8", "replace"), err.decode("utf-8", "replace"), timed_out=True)
    if ctx is not None:
        ctx.check_cancel()
    return CommandResult(process.returncode, out.decode("utf-8", "replace"), err.decode("utf-8", "replace"))


@dataclass
class TailRead:
    text: str
    offset: int
    size: int
    sha256: str
    mtime: str


def read_tail(path: Path, limit: int) -> TailRead:
    """Últimos `limit` bytes; o hash cobre exatamente o trecho lido."""
    with path.open("rb") as handle:
        size = handle.seek(0, os.SEEK_END)
        offset = max(0, size - limit)
        handle.seek(offset)
        data = handle.read(limit)
    return TailRead(data.decode("utf-8", "replace"), offset, size, sha256_bytes(data), iso_mtime(path))


def read_head(path: Path, limit: int = 16_384) -> str:
    with path.open("rb") as handle:
        return handle.read(limit).decode("utf-8", "replace")
