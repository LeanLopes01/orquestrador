"""Contratos da ingestão. Valores ausentes ficam None, nunca strings de sucesso."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Status(StrEnum):
    QUEUED = "queued"
    VALIDATING = "validating"
    FETCHING = "fetching"
    READING_CACHE = "reading_cache"
    RETRYING = "retrying"
    EXTRACTING = "extracting"
    WRITING = "writing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


TERMINAL = {Status.COMPLETED, Status.FAILED, Status.SKIPPED, Status.CANCELLED, Status.INTERRUPTED}


class SourceFailure(Exception):
    """Fim de uma fonte com estado terminal e motivo estável."""

    def __init__(self, status: Status, reason: str, message: str, **extra: Any) -> None:
        super().__init__(message)
        self.status = status
        self.reason = reason
        self.message = message
        self.extra = extra


class RetryableFailure(Exception):
    def __init__(self, reason: str, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message
        self.retry_after = retry_after


@dataclass
class RawSource:
    original_url: str
    catalog_id: str | None = None
    curation: dict[str, Any] | None = None
    include_comments: bool | None = None


@dataclass(frozen=True)
class SourceSpec:
    kind: str  # article | video
    original_url: str
    canonical_url: str
    source_id: str
    video_id: str | None = None


@dataclass
class AcquiredSource:
    """Aquisição em cache: HTML de artigo ou JSON de legenda."""

    source_id: str
    kind: str
    revision: str
    acquired_at: str
    final_url: str | None
    body_path: str
    body_sha256: str
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedDocument:
    title: str
    body: str
    language: str | None = None
    caption: str | None = None  # manual | automática
    warnings: list[str] = field(default_factory=list)


@dataclass
class StoredDocument:
    path: str
    sha256: str
    bytes: int


@dataclass
class SourceResult:
    source_id: str | None
    original_url: str
    canonical_url: str | None
    final_url: str | None
    kind: str | None
    status: str
    reason_code: str | None
    message: str
    attempts: int = 0
    acquired_at: str | None = None
    extracted_at: str | None = None
    duration_ms: int = 0
    output_path: str | None = None
    hash: str | None = None
    language: str | None = None
    warnings: list[str] = field(default_factory=list)
    catalog_id: str | None = None
    cache_origin: str | None = None
    noop: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProgressEvent:
    batch_id: str
    source_id: str | None
    stage: str
    status: str
    timestamp: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
