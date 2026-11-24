"""Contratos internos (seção 5 do plano). Sem acoplamento a HTTP ou UI."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class IndexReport:
    scope: str
    added: int = 0
    updated: int = 0
    removed: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RetrievedSource:
    id: str  # S1, S2... estável dentro da resposta
    record_id: str
    kind: str  # code_pointer | documentation
    filepath: str
    relpath: str
    text: str
    distance: float
    hash: str
    read_at: str
    lines: tuple[int, int] | None = None
    chunk_index: int | None = None
    state: str = "current"  # current | stale_summary | snapshot
    section: str | None = None
    full_file: bool = False
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, *, include_text: bool = True, text_limit: int | None = None) -> dict[str, Any]:
        data = asdict(self)
        if not include_text:
            data.pop("text")
        elif text_limit is not None and len(self.text) > text_limit:
            data["text"] = self.text[:text_limit]
            data["text_truncated"] = True
        return data


@dataclass
class RetrievalResult:
    query: str
    sources: list[RetrievedSource]
    warnings: list[str]
    bytes_read: int
    files_read: list[str]
    timings_ms: dict[str, int] = field(default_factory=dict)

    def to_dict(self, *, text_limit: int | None = None) -> dict[str, Any]:
        return {
            "query": self.query,
            "sources": [s.to_dict(text_limit=text_limit) for s in self.sources],
            "warnings": self.warnings,
            "bytes_read": self.bytes_read,
            "files_read": self.files_read,
            "timings_ms": self.timings_ms,
        }


@dataclass
class ContextBundle:
    text: str
    prompt: str
    included: list[dict[str, Any]]
    omitted: list[dict[str, Any]]
    warnings: list[str]
    token_count: int
    tokenizer: str
    budget: int


@dataclass
class AnswerResult:
    answer: str
    sources: list[dict[str, Any]]
    warnings: list[str]
    timings_ms: dict[str, int]
    model: str
    prompt_tokens: int
    generated_tokens: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProgressEvent:
    request_id: str
    stage: str
    message: str
    elapsed_ms: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
