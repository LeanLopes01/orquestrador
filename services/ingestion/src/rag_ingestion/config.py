"""TOML de configuração. Caminhos relativos resolvem a partir do próprio arquivo."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class NetworkPolicy:
    timeout_seconds: float = 20.0
    max_attempts: int = 3
    backoff_seconds: tuple[float, ...] = (2.0, 4.0)
    retry_budget_seconds: float = 60.0
    source_deadline_seconds: float = 90.0
    max_html_bytes: int = 10 * 1024 * 1024
    max_redirects: int = 5
    domain_pause_seconds: float = 1.0
    user_agent: str = "DiceVTT-RAG-Ingestion/0.1"


@dataclass(frozen=True)
class IngestionConfig:
    config_path: Path
    project_id: str
    output_root: Path
    state_path: Path
    cache_root: Path
    manifests_root: Path
    log_path: Path
    token_path: Path
    catalog_path: Path | None = None
    languages: tuple[str, ...] = ("pt-BR", "pt", "en")
    default_mode: str = "online"
    host: str = "127.0.0.1"
    port: int = 8766
    network: NetworkPolicy = field(default_factory=NetworkPolicy)
    min_chars: int = 200
    include_comments: bool = False
    cache_disk_limit_mb: int = 2048


def _path(base: Path, value: object, name: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{name} precisa ser um caminho.")
    path = Path(value)
    return (path if path.is_absolute() else base / path).resolve()


def load_config(path: str | Path) -> IngestionConfig:
    config_path = Path(path).resolve()
    try:
        data = tomllib.loads(config_path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise ConfigError(f"Configuração não encontrada: {config_path}") from None
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"TOML inválido em {config_path}: {exc}") from None
    base = config_path.parent
    project_id = str(data.get("project_id", "")).strip()
    if not project_id or not project_id.replace("-", "").replace("_", "").isalnum():
        raise ConfigError("project_id precisa ser alfanumérico (ex.: dicevtt).")
    service = data.get("service", {})
    net = data.get("network", {})
    extraction = data.get("extraction", {})
    mode = str(data.get("default_mode", "online"))
    if mode not in {"online", "offline"}:
        raise ConfigError("default_mode deve ser online ou offline.")
    languages = tuple(str(x) for x in data.get("languages", ["pt-BR", "pt", "en"]))
    if not languages:
        raise ConfigError("languages não pode ser vazio.")
    try:
        network = NetworkPolicy(
            timeout_seconds=float(net.get("timeout_seconds", 20)),
            max_attempts=max(1, int(net.get("max_attempts", 3))),
            backoff_seconds=tuple(float(x) for x in net.get("backoff_seconds", [2, 4])),
            retry_budget_seconds=float(net.get("retry_budget_seconds", 60)),
            source_deadline_seconds=float(net.get("source_deadline_seconds", 90)),
            max_html_bytes=int(net.get("max_html_bytes", 10 * 1024 * 1024)),
            max_redirects=int(net.get("max_redirects", 5)),
            domain_pause_seconds=float(net.get("domain_pause_seconds", 1.0)),
            user_agent=str(net.get("user_agent", NetworkPolicy.user_agent)),
        )
        return IngestionConfig(
            config_path=config_path,
            project_id=project_id,
            output_root=_path(base, data.get("output_root", "../documentacao_rag"), "output_root"),
            state_path=_path(base, data.get("state_path", "ingestion/state.sqlite3"), "state_path"),
            cache_root=_path(base, data.get("cache_root", "ingestion/cache"), "cache_root"),
            manifests_root=_path(base, data.get("manifests_root", "ingestion/manifests"), "manifests_root"),
            log_path=_path(base, data.get("log_path", "ingestion/logs/events.jsonl"), "log_path"),
            token_path=_path(base, data.get("token_path", "ingestion/api-token"), "token_path"),
            catalog_path=_path(base, data["catalog_path"], "catalog_path") if data.get("catalog_path") else None,
            languages=languages,
            default_mode=mode,
            host=str(service.get("host", "127.0.0.1")),
            port=int(service.get("port", 8766)),
            network=network,
            min_chars=int(extraction.get("min_chars", 200)),
            include_comments=bool(extraction.get("include_comments", False)),
            cache_disk_limit_mb=int(extraction.get("cache_disk_limit_mb", 2048)),
        )
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"Valor inválido na configuração: {exc}") from None
