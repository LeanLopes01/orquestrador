"""TOML do runner. Caminhos relativos resolvem a partir do próprio arquivo; ${VAR} expande o ambiente."""

from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

_VAR = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class RagLink:
    """O que o runner precisa do RAG: só leitura do health e a raiz que ele indexa."""

    port: int
    token_path: Path
    scripts_root: Path


@dataclass(frozen=True)
class Validator:
    """Um -executeMethod do projeto que roda em lote, grava um relatório e sai com 0 (ok) ou 1."""

    id: str
    name: str
    method: str
    report_arg: str
    extra_args: tuple[str, ...] = ()
    timeout_seconds: float = 900.0
    graphics: bool = True  # False acrescenta -nographics


@dataclass(frozen=True)
class FullAudit:
    audit_root: Path
    deadline_seconds: float = 3600.0
    unity_timeout_seconds: float = 1800.0
    import_timeout_seconds: float = 2700.0
    copy_dirs: tuple[str, ...] = ("Assets", "Packages", "ProjectSettings")
    provision: tuple[str, ...] = ()
    product_suffix: str = "-Audit"
    validators: tuple[Validator, ...] = ()


@dataclass(frozen=True)
class AiConfig:
    max_findings: int = 3
    local_timeout_seconds: float = 900.0  # por ocorrência: o AirLLM gera ~1 token/s no CPU
    total_timeout_seconds: float = 2700.0
    claude_command: str = "claude"
    claude_model: str = "sonnet"
    claude_timeout_seconds: float = 300.0


@dataclass(frozen=True)
class DiagnosticsConfig:
    config_path: Path
    project_id: str
    project_name: str
    project_root: Path
    state_path: Path
    settings_path: Path
    runs_root: Path
    log_dir: Path
    token_path: Path
    host: str = "127.0.0.1"
    port: int = 8768
    light_deadline_seconds: float = 90.0
    command_timeout_seconds: float = 20.0
    rag_wait_seconds: float = 30.0  # na abertura o RAG sobe junto com o runner
    log_read_bytes: int = 2 * 1024 * 1024
    max_findings_per_check: int = 40
    scan_file_limit: int = 60_000
    git: str = "git"
    plastic_cm: Path | None = None
    unity_editors: Path | None = None
    editor_log: Path | None = None
    player_log_dir: Path | None = None
    rag: RagLink | None = None
    full: FullAudit | None = None
    ai: AiConfig = AiConfig()


def _expand(value: str) -> str:
    def sub(match: re.Match[str]) -> str:
        found = os.environ.get(match.group(1))
        if found is None:
            raise ConfigError(f"Variável de ambiente ausente: {match.group(1)}")
        return found

    return _VAR.sub(sub, value)


def _path(base: Path, value: object, name: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{name} precisa ser um caminho.")
    path = Path(_expand(value))
    return (path if path.is_absolute() else base / path).resolve()


def _optional(base: Path, value: object, name: str) -> Path | None:
    return _path(base, value, name) if value else None


def _rag_link(base: Path, value: object) -> RagLink | None:
    if not value:
        return None
    rag_path = _path(base, value, "rag.config")
    try:
        data = tomllib.loads(rag_path.read_text(encoding="utf-8-sig"))
    except (OSError, tomllib.TOMLDecodeError):
        return None  # sem RAG configurado o check registra indisponível, não quebra o runner
    rag_base = rag_path.parent
    return RagLink(
        port=int(data.get("service", {}).get("port", 8767)),
        token_path=_path(rag_base, data.get("token_path", "rag/api-token"), "rag.token_path"),
        scripts_root=_path(rag_base, data.get("scripts_root", ""), "rag.scripts_root"),
    )


def _ascii_dir(base: Path, value: object, name: str) -> Path:
    path = _path(base, value, name)
    if not str(path).isascii():
        raise ConfigError(f"{name} precisa ser um caminho ASCII (a Unity e o Chroma tropeçam em acentos): {path}")
    return path


def _full(base: Path, data: dict, project_root: Path) -> FullAudit | None:
    if not data:
        return None
    root = _ascii_dir(base, data.get("audit_root"), "full.audit_root")
    if root == project_root or root.is_relative_to(project_root) or project_root.is_relative_to(root):
        raise ConfigError("full.audit_root não pode conter o projeto nem estar dentro dele.")
    validators = []
    for item in data.get("validators", []):
        if not item.get("enabled", True):
            continue
        if not re.fullmatch(r"[a-z0-9_-]{1,40}", str(item.get("id", ""))):
            raise ConfigError("full.validators.id precisa ser minúsculo e alfanumérico.")
        if not re.fullmatch(r"[A-Za-z_][\w.]*\.[A-Za-z_]\w*", str(item.get("method", ""))):
            raise ConfigError(f"full.validators.{item['id']}.method inválido.")
        if not re.fullmatch(r"-[A-Za-z]\w*", str(item.get("report_arg", ""))):
            raise ConfigError(f"full.validators.{item['id']}.report_arg inválido.")
        validators.append(Validator(
            id=item["id"], name=str(item.get("name") or item["id"]), method=item["method"],
            report_arg=item["report_arg"], extra_args=tuple(str(a) for a in item.get("extra_args", [])),
            timeout_seconds=float(item.get("timeout_seconds", 900)), graphics=bool(item.get("graphics", True)),
        ))
    return FullAudit(
        audit_root=root,
        deadline_seconds=float(data.get("deadline_seconds", 3600)),
        unity_timeout_seconds=float(data.get("unity_timeout_seconds", 1800)),
        import_timeout_seconds=float(data.get("import_timeout_seconds", 2700)),
        copy_dirs=tuple(data.get("copy_dirs", ["Assets", "Packages", "ProjectSettings"])),
        provision=tuple(data.get("provision", [])),
        product_suffix=str(data.get("product_suffix", "-Audit")),
        validators=tuple(validators),
    )


def _ai(data: dict) -> AiConfig:
    return AiConfig(
        max_findings=max(1, int(data.get("max_findings", 3))),
        local_timeout_seconds=float(data.get("local_timeout_seconds", 900)),
        total_timeout_seconds=float(data.get("total_timeout_seconds", 2700)),
        claude_command=str(data.get("claude_command", "claude")),
        claude_model=str(data.get("claude_model", "sonnet")),
        claude_timeout_seconds=float(data.get("claude_timeout_seconds", 300)),
    )


def load_config(path: str | Path) -> DiagnosticsConfig:
    config_path = Path(path).resolve()
    try:
        data = tomllib.loads(config_path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise ConfigError(f"Configuração não encontrada: {config_path}") from None
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"TOML inválido em {config_path}: {exc}") from None
    base = config_path.parent
    project_id = str(data.get("project_id", "")).strip()
    if not re.fullmatch(r"[a-z0-9_-]{1,40}", project_id):
        raise ConfigError("project_id precisa ser minúsculo e alfanumérico (ex.: dicevtt).")
    service, limits = data.get("service", {}), data.get("limits", {})
    tools, logs = data.get("tools", {}), data.get("logs", {})
    try:
        project_root = _path(base, data.get("project_root"), "project_root")
        return DiagnosticsConfig(
            config_path=config_path,
            project_id=project_id,
            project_name=str(data.get("project_name") or project_id),
            project_root=project_root,
            state_path=_path(base, data.get("state_path", "audits/audits.sqlite3"), "state_path"),
            settings_path=_path(base, data.get("settings_path", "audits/config.json"), "settings_path"),
            runs_root=_path(base, data.get("runs_root", "audits/runs"), "runs_root"),
            log_dir=_path(base, data.get("log_dir", "audits/logs"), "log_dir"),
            token_path=_path(base, data.get("token_path", "audits/api-token"), "token_path"),
            host=str(service.get("host", "127.0.0.1")),
            port=int(service.get("port", 8768)),
            light_deadline_seconds=float(limits.get("light_deadline_seconds", 90)),
            command_timeout_seconds=float(limits.get("command_timeout_seconds", 20)),
            rag_wait_seconds=float(limits.get("rag_wait_seconds", 30)),
            log_read_bytes=int(limits.get("log_read_bytes", 2 * 1024 * 1024)),
            max_findings_per_check=int(limits.get("max_findings_per_check", 40)),
            scan_file_limit=int(limits.get("scan_file_limit", 60_000)),
            git=str(tools.get("git", "git")),
            plastic_cm=_optional(base, tools.get("plastic_cm"), "tools.plastic_cm"),
            unity_editors=_optional(base, tools.get("unity_editors"), "tools.unity_editors"),
            editor_log=_optional(base, logs.get("editor_log"), "logs.editor_log"),
            player_log_dir=_optional(base, logs.get("player_log_dir"), "logs.player_log_dir"),
            rag=_rag_link(base, data.get("rag", {}).get("config")),
            full=_full(base, data.get("full", {}), project_root),
            ai=_ai(data.get("ai", {})),
        )
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"Valor inválido em {config_path}: {exc}") from None
