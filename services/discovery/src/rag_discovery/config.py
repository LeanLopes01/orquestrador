"""TOML de configuração. Caminhos relativos resolvem a partir do próprio arquivo.

A descoberta não duplica caminhos: lê ingestion.toml (estado, token, porta) e rag.toml
(scripts, embeddings, gerador AirLLM, token, porta) pelos carregadores de cada serviço.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

CATALOG_KINDS = {"unity_pages", "unity_toc", "docfx_xrefmap", "html_links"}


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class CatalogSpec:
    """Índice oficial de uma documentação.

    api: entradas podem casar com símbolos usados no código (tipos/membros).
    topics: entradas entram na busca semântica por tópicos (títulos/breadcrumbs).
    """

    id: str
    kind: str
    index: str
    base: str
    namespace: str | None = None
    api: bool = False
    topics: bool = False
    path_prefix: str | None = None


@dataclass(frozen=True)
class DiscoveryConfig:
    config_path: Path
    ingestion_config: Path
    rag_config: Path
    state_path: Path
    cache_root: Path
    catalogs: tuple[CatalogSpec, ...]
    catalog_ttl_days: float = 7.0
    max_api_per_run: int = 25
    max_topic_per_run: int = 15
    min_files_per_symbol: int = 1
    include_members: bool = True
    min_score: float = 0.45
    results_per_topic: int = 3
    topics: tuple[str, ...] = ()
    use_recent_asks: bool = True
    llm_enabled: bool = True
    llm_topics: int = 8
    llm_max_new_tokens: int = 160
    poll_seconds: float = 3.0
    batch_timeout_minutes: float = 60.0
    user_agent: str = "DiceVTT-RAG-Discovery/0.1 (descoberta local; uso pessoal)"


def _path(base: Path, value: object, name: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{name} precisa ser um caminho.")
    path = Path(value)
    return (path if path.is_absolute() else base / path).resolve()


def _catalog(entry: object, index: int) -> CatalogSpec:
    if not isinstance(entry, dict):
        raise ConfigError(f"catalogs[{index}] precisa ser uma tabela.")
    for name in ("id", "kind", "index", "base"):
        if not isinstance(entry.get(name), str) or not entry[name].strip():
            raise ConfigError(f"catalogs[{index}].{name} ausente.")
    if entry["kind"] not in CATALOG_KINDS:
        raise ConfigError(f"catalogs[{index}].kind deve ser um de {sorted(CATALOG_KINDS)}.")
    for name in ("index", "base"):
        if not entry[name].startswith("https://"):
            raise ConfigError(f"catalogs[{index}].{name} precisa ser https://.")
    if not entry.get("api") and not entry.get("topics"):
        raise ConfigError(f"catalogs[{index}] precisa de api = true e/ou topics = true.")
    return CatalogSpec(
        id=entry["id"], kind=entry["kind"], index=entry["index"], base=entry["base"],
        namespace=str(entry["namespace"]) if entry.get("namespace") else None,
        api=bool(entry.get("api", False)), topics=bool(entry.get("topics", False)),
        path_prefix=str(entry["path_prefix"]) if entry.get("path_prefix") else None,
    )


def load_config(path: str | Path) -> DiscoveryConfig:
    config_path = Path(path).resolve()
    try:
        data = tomllib.loads(config_path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise ConfigError(f"Configuração não encontrada: {config_path}") from None
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"TOML inválido em {config_path}: {exc}") from None
    base = config_path.parent
    limits = data.get("limits", {})
    topics = data.get("topics", {})
    llm = data.get("llm", {})
    run = data.get("run", {})
    catalogs = tuple(_catalog(entry, i) for i, entry in enumerate(data.get("catalogs", [])))
    if not catalogs:
        raise ConfigError("Configure ao menos um [[catalogs]].")
    if len({c.id for c in catalogs}) != len(catalogs):
        raise ConfigError("IDs de catálogo repetidos.")
    try:
        return DiscoveryConfig(
            config_path=config_path,
            ingestion_config=_path(base, data.get("ingestion_config", "ingestion.toml"), "ingestion_config"),
            rag_config=_path(base, data.get("rag_config", "rag.toml"), "rag_config"),
            state_path=_path(base, data.get("state_path", "discovery/state.sqlite3"), "state_path"),
            cache_root=_path(base, data.get("cache_root", "discovery/cache"), "cache_root"),
            catalogs=catalogs,
            catalog_ttl_days=float(data.get("catalog_ttl_days", 7)),
            max_api_per_run=max(0, int(limits.get("max_api_per_run", 25))),
            max_topic_per_run=max(0, int(limits.get("max_topic_per_run", 15))),
            min_files_per_symbol=max(1, int(limits.get("min_files_per_symbol", 1))),
            include_members=bool(limits.get("include_members", True)),
            min_score=float(topics.get("min_score", 0.45)),
            results_per_topic=max(1, int(topics.get("results_per_topic", 3))),
            topics=tuple(str(t).strip() for t in topics.get("extra", []) if str(t).strip()),
            use_recent_asks=bool(topics.get("use_recent_asks", True)),
            llm_enabled=bool(llm.get("enabled", True)),
            llm_topics=max(1, int(llm.get("topics", 8))),
            llm_max_new_tokens=max(32, int(llm.get("max_new_tokens", 160))),
            poll_seconds=max(0.5, float(run.get("poll_seconds", 3))),
            batch_timeout_minutes=max(1.0, float(run.get("batch_timeout_minutes", 60))),
            user_agent=str(data.get("user_agent", DiscoveryConfig.user_agent)),
        )
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"Valor inválido na configuração: {exc}") from None
