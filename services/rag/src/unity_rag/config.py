"""TOML + ambiente + validação. Relativos resolvem a partir do arquivo de configuração."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class EmbeddingConfig:
    repo_id: str
    local_dir: Path
    revision: str = ""
    device: str = "cpu"
    normalize: bool = True
    batch_size: int = 32


@dataclass(frozen=True)
class RetrievalConfig:
    code_top_k: int = 4
    doc_top_k: int = 4
    candidate_cap: int = 12
    max_script_bytes: int = 1024 * 1024
    read_attempts: int = 3
    max_query_chars: int = 2000


@dataclass(frozen=True)
class ChunkingConfig:
    chunk_tokens: int = 200
    overlap_tokens: int = 30
    fallback_encoding: str = "cp1252"


@dataclass(frozen=True)
class WatcherConfig:
    enabled: bool = True
    debounce_ms: int = 500
    queue_limit: int = 2000


@dataclass(frozen=True)
class GeneratorConfig:
    enabled: bool = False
    repo_id: str = ""
    model_path: Path | None = None
    shards_path: Path | None = None
    device: str = "cpu"
    dtype: str = "float32"
    max_seq_len: int = 2048
    max_new_tokens: int = 384
    compression: str = ""
    prefetching: bool = False


@dataclass(frozen=True)
class RagConfig:
    config_path: Path
    project_id: str
    unity_project_root: Path
    scripts_root: Path
    docs_root: Path
    chroma_path: Path
    index_state_path: Path
    token_path: Path
    log_dir: Path
    embedding: EmbeddingConfig
    offline: bool = True
    host: str = "127.0.0.1"
    port: int = 8767
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    watcher: WatcherConfig = field(default_factory=WatcherConfig)
    generator: GeneratorConfig = field(default_factory=GeneratorConfig)
    result_ttl_hours: float = 24.0
    ask_queue_limit: int = 4

    @property
    def lock_path(self) -> Path:
        return self.index_state_path.with_name("service.lock")


def _path(base: Path, value: object, name: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{name} precisa ser um caminho.")
    path = Path(os.path.expandvars(value))
    return (path if path.is_absolute() else base / path).resolve()


def load_config(path: str | Path) -> RagConfig:
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
    emb = data.get("embedding", {})
    ret = data.get("retrieval", {})
    chk = data.get("chunking", {})
    wat = data.get("watcher", {})
    gen = data.get("generator", {})
    svc = data.get("service", {})
    jobs = data.get("jobs", {})
    try:
        embedding = EmbeddingConfig(
            repo_id=str(emb.get("repo_id", "sentence-transformers/all-MiniLM-L6-v2")),
            local_dir=_path(base, emb.get("local_dir", "rag/models/embeddings/all-MiniLM-L6-v2"), "embedding.local_dir"),
            revision=str(emb.get("revision", "")),
            device=str(emb.get("device", "cpu")),
            normalize=bool(emb.get("normalize", True)),
            batch_size=int(emb.get("batch_size", 32)),
        )
        chunking = ChunkingConfig(
            chunk_tokens=int(chk.get("chunk_tokens", 200)),
            overlap_tokens=int(chk.get("overlap_tokens", 30)),
            fallback_encoding=str(chk.get("fallback_encoding", "cp1252")),
        )
        if not 0 <= chunking.overlap_tokens < chunking.chunk_tokens:
            raise ConfigError("overlap_tokens precisa ser menor que chunk_tokens.")
        generator = GeneratorConfig(
            enabled=bool(gen.get("enabled", False)) and bool(gen.get("model_path")),
            repo_id=str(gen.get("repo_id", "")),
            model_path=_path(base, gen["model_path"], "generator.model_path") if gen.get("model_path") else None,
            shards_path=_path(base, gen.get("shards_path", "rag/shards"), "generator.shards_path"),
            device=str(gen.get("device", "cpu")),
            dtype=str(gen.get("dtype", "float32")),
            max_seq_len=int(gen.get("max_seq_len", 2048)),
            max_new_tokens=int(gen.get("max_new_tokens", 384)),
            compression=str(gen.get("compression", "")),
            prefetching=bool(gen.get("prefetching", False)),
        )
        if generator.dtype not in {"float32", "bfloat16", "float16"}:
            raise ConfigError("generator.dtype deve ser float32, bfloat16 ou float16.")
        if generator.compression not in {"", "4bit", "8bit"}:
            raise ConfigError("generator.compression deve ser vazio, 4bit ou 8bit.")
        chroma_path = _path(base, data.get("chroma_path", "rag/chroma"), "chroma_path")
        if os.name == "nt" and not str(chroma_path).isascii():
            # Chroma 1.5 (Rust/hnswlib) grava mas não reabre o índice HNSW em caminhos com
            # acentos no Windows ("Error loading hnsw index"); comprovado neste PC.
            raise ConfigError(
                f"chroma_path precisa ser um caminho ASCII no Windows (recebido {chroma_path}). "
                "Use, por exemplo, chroma_path = \"${LOCALAPPDATA}/DiceVTT-RAG/chroma\"."
            )
        return RagConfig(
            config_path=config_path,
            project_id=project_id,
            unity_project_root=_path(base, data.get("unity_project_root", ""), "unity_project_root"),
            scripts_root=_path(base, data.get("scripts_root", ""), "scripts_root"),
            docs_root=_path(base, data.get("docs_root", "../documentacao_rag"), "docs_root"),
            chroma_path=chroma_path,
            index_state_path=_path(base, data.get("index_state_path", "rag/index-state.sqlite3"), "index_state_path"),
            token_path=_path(base, data.get("token_path", "rag/api-token"), "token_path"),
            log_dir=_path(base, data.get("log_dir", "rag/logs"), "log_dir"),
            embedding=embedding,
            offline=bool(data.get("offline", True)),
            host=str(svc.get("host", "127.0.0.1")),
            port=int(svc.get("port", 8767)),
            retrieval=RetrievalConfig(
                code_top_k=int(ret.get("code_top_k", 4)),
                doc_top_k=int(ret.get("doc_top_k", 4)),
                candidate_cap=int(ret.get("candidate_cap", 12)),
                max_script_bytes=int(ret.get("max_script_bytes", 1024 * 1024)),
                read_attempts=max(1, int(ret.get("read_attempts", 3))),
                max_query_chars=int(ret.get("max_query_chars", 2000)),
            ),
            chunking=chunking,
            watcher=WatcherConfig(
                enabled=bool(wat.get("enabled", True)),
                debounce_ms=int(wat.get("debounce_ms", 500)),
                queue_limit=int(wat.get("queue_limit", 2000)),
            ),
            generator=generator,
            result_ttl_hours=float(jobs.get("result_ttl_hours", 24)),
            ask_queue_limit=max(1, int(jobs.get("ask_queue_limit", 4))),
        )
    except (TypeError, ValueError, KeyError) as exc:
        raise ConfigError(f"Valor inválido na configuração: {exc}") from None


def apply_offline_environment(config: RagConfig) -> None:
    """Antes de importar transformers/sentence-transformers/chromadb."""
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    if config.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
