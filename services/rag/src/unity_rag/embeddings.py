"""Serviço compartilhado de embeddings: o mesmo encoder na indexação e nas consultas.

Chunks são medidos com o tokenizer do próprio SentenceTransformer (não do gerador),
respeitando max_seq_length para não depender de truncamento silencioso.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import threading
from pathlib import Path
from typing import Protocol

from .config import EmbeddingConfig

SPECIAL_TOKEN_RESERVE = 2  # [CLS]/[SEP] ou <s>/</s>


class EmbeddingUnavailable(Exception):
    pass


class Embedder(Protocol):
    name: str

    @property
    def signature(self) -> dict[str, object]: ...

    @property
    def max_tokens(self) -> int: ...

    def encode(self, texts: list[str]) -> list[list[float]]: ...

    def token_spans(self, text: str) -> list[tuple[int, int]]: ...

    def count_tokens(self, text: str) -> int: ...


def collection_name(signature: dict[str, object]) -> str:
    digest = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()[:12]
    return f"unity_rag_{digest}"


def model_revision(local_dir: Path) -> str:
    try:
        return str(json.loads((local_dir / "rag-model.json").read_text(encoding="utf-8")).get("revision", ""))
    except (OSError, ValueError):
        return ""


class SentenceTransformerEmbedder:
    def __init__(self, config: EmbeddingConfig) -> None:
        if not (config.local_dir / "modules.json").exists() and not (config.local_dir / "config.json").exists():
            raise EmbeddingUnavailable(
                f"Modelo de embeddings ausente em {config.local_dir}. Rode `unity_rag prepare-models`."
            )
        from sentence_transformers import SentenceTransformer

        self._config = config
        self._model = SentenceTransformer(str(config.local_dir), device=config.device, local_files_only=True)
        self._tokenizer = self._model.tokenizer
        self._lock = threading.Lock()
        self.name = config.repo_id
        self._revision = config.revision or model_revision(config.local_dir)
        get_dim = getattr(self._model, "get_embedding_dimension", None) or self._model.get_sentence_embedding_dimension
        self._dim = int(get_dim())

    @property
    def signature(self) -> dict[str, object]:
        return {"model": self.name, "revision": self._revision, "dim": self._dim,
                "normalize": self._config.normalize, "metric": "cosine", "schema": 1}

    @property
    def max_tokens(self) -> int:
        return int(self._model.max_seq_length) - SPECIAL_TOKEN_RESERVE

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        with self._lock:
            vectors = self._model.encode(
                texts, batch_size=self._config.batch_size, normalize_embeddings=self._config.normalize,
                convert_to_numpy=True, show_progress_bar=False,
            )
        return [v.tolist() for v in vectors]

    def token_spans(self, text: str) -> list[tuple[int, int]]:
        with self._lock:
            encoded = self._tokenizer(text, add_special_tokens=False, return_offsets_mapping=True,
                                      truncation=False, verbose=False)
        return [(int(a), int(b)) for a, b in encoded["offset_mapping"] if b > a]

    def count_tokens(self, text: str) -> int:
        with self._lock:
            return len(self._tokenizer(text, add_special_tokens=False, truncation=False, verbose=False)["input_ids"])


class HashEmbedder:
    """Embeddings determinísticos para testes: valida lógica, não qualidade semântica."""

    name = "test/hash-embedder"
    _word = re.compile(r"\w+|[^\w\s]", re.UNICODE)

    def __init__(self, dim: int = 64, max_tokens: int = 128) -> None:
        self._dim = dim
        self._max = max_tokens
        self.calls = 0

    @property
    def signature(self) -> dict[str, object]:
        return {"model": self.name, "revision": "1", "dim": self._dim, "normalize": True, "metric": "cosine", "schema": 1}

    @property
    def max_tokens(self) -> int:
        return self._max

    def encode(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        out = []
        for text in texts:
            vector = [0.0] * self._dim
            for token in self._word.findall(text.lower()):
                if len(token) < 3:
                    continue
                vector[int(hashlib.md5(token.encode()).hexdigest(), 16) % self._dim] += 1.0
            norm = math.sqrt(sum(v * v for v in vector)) or 1.0
            out.append([v / norm for v in vector])
        return out

    def token_spans(self, text: str) -> list[tuple[int, int]]:
        return [m.span() for m in self._word.finditer(text)]

    def count_tokens(self, text: str) -> int:
        return len(self._word.findall(text))
