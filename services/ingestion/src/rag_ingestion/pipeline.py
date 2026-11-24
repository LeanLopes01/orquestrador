"""Processamento sequencial de lotes: cada fonte termina isolada, com estado e motivo.

Rede só no modo online e só nas funções de aquisição (injetáveis para os testes).
Extração e escrita sempre a partir do cache local.
"""

from __future__ import annotations

import hashlib
import json
import random
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from . import FORMAT_SCHEMA, __version__
from .acquisition import (
    HttpResponse,
    RedirectedToVideo,
    decode_html,
    fetch_web_page,
    load_cached_source,
    now_iso,
    save_to_cache,
)
from .config import IngestionConfig, NetworkPolicy
from .events import EventLog
from .formatter import body_hash, build_markdown
from .models import (
    AcquiredSource,
    ExtractedDocument,
    RawSource,
    RetryableFailure,
    SourceFailure,
    SourceResult,
    SourceSpec,
    Status,
)
from .repository import Repository
from .storage import document_name, sha256_file, write_document_atomic
from .urls import UrlError, classify, redact
from .web_extractor import extract_article
from .youtube_extractor import format_transcript, load_transcript, select_and_fetch

PageFetcher = Callable[[str, NetworkPolicy, float | None], HttpResponse]
TranscriptFetcher = Callable[[str, tuple[str, ...], NetworkPolicy], dict[str, Any]]


def _default_page(url: str, policy: NetworkPolicy, deadline: float | None) -> HttpResponse:
    return fetch_web_page(url, policy, deadline=deadline)


@dataclass
class Pipeline:
    config: IngestionConfig
    repository: Repository
    events: EventLog
    fetch_page: PageFetcher = _default_page
    fetch_transcript: TranscriptFetcher = select_and_fetch
    sleep: Callable[[float], None] = time.sleep
    cancel: threading.Event = field(default_factory=threading.Event)
    _last_hit: dict[str, float] = field(default_factory=dict)

    # Aquisição -----------------------------------------------------------------

    def _pause_for(self, host: str) -> None:
        last = self._last_hit.get(host)
        if last is not None:
            wait = self.config.network.domain_pause_seconds - (time.monotonic() - last)
            if wait > 0:
                self.sleep(wait)
        self._last_hit[host] = time.monotonic()

    def _with_retries(self, work: Callable[[float], Any], batch_id: str, spec: SourceSpec) -> tuple[Any, int]:
        policy = self.config.network
        deadline = time.monotonic() + policy.source_deadline_seconds
        waited = 0.0
        attempt = 0
        while True:
            attempt += 1
            try:
                return work(deadline), attempt
            except RetryableFailure as exc:
                if attempt >= policy.max_attempts:
                    raise SourceFailure(Status.FAILED, exc.reason, f"{exc.message} Tentativas esgotadas.",
                                        attempts=attempt) from None
                delay = exc.retry_after
                if delay is None:
                    base = policy.backoff_seconds[min(attempt - 1, len(policy.backoff_seconds) - 1)] if policy.backoff_seconds else 2.0
                    delay = base * random.uniform(0.8, 1.2)
                remaining = min(policy.retry_budget_seconds - waited, deadline - time.monotonic())
                if delay > remaining:
                    retry_at = time.time() + delay
                    raise SourceFailure(
                        Status.FAILED, "retry_budget_exceeded",
                        f"{exc.message} Nova tentativa só depois de {delay:.0f}s, acima do orçamento.",
                        attempts=attempt,
                        retry_after_at=time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(retry_at)),
                    ) from None
                self.events.emit(batch_id, spec.source_id, "fetching", Status.RETRYING.value,
                                 f"{exc.reason}: nova tentativa em {delay:.1f}s")
                if self.cancel.wait(delay):
                    raise SourceFailure(Status.CANCELLED, "cancelled", "Cancelado durante a espera.") from None
                waited += delay

    def _acquire_online(self, spec: SourceSpec, batch_id: str) -> tuple[SourceSpec, AcquiredSource, int]:
        cache_root = self.config.cache_root
        if spec.kind == "article":
            def fetch(deadline: float) -> HttpResponse:
                self._pause_for(urlsplit(spec.canonical_url).hostname or "")
                return self.fetch_page(spec.canonical_url, self.config.network, deadline)

            try:
                response, attempts = self._with_retries(fetch, batch_id, spec)
            except RedirectedToVideo as redirect:
                try:
                    target = classify(redirect.url)
                except UrlError:
                    raise SourceFailure(Status.FAILED, "unsupported_redirect",
                                        "Redirecionou para uma página do YouTube que não é um vídeo.") from None
                if target.kind != "video":
                    raise SourceFailure(Status.FAILED, "unsupported_redirect", "Redirecionamento não suportado.") from None
                video = SourceSpec("video", spec.original_url, target.canonical_url, target.source_id, target.video_id)
                return self._acquire_online(video, batch_id)
            meta = {"acquired_at": response.acquired_at, "final_url": response.final_url, "status": response.status,
                    "mime": response.mime, "charset": response.charset, "redirects": response.redirects,
                    "original_url": spec.original_url, "canonical_url": spec.canonical_url}
            return spec, save_to_cache(cache_root, spec.source_id, "article", response.body, meta), attempts

        def fetch_video(deadline: float) -> dict[str, Any]:
            self._pause_for("youtube.com")
            return self.fetch_transcript(spec.video_id or "", self.config.languages, self.config.network)

        data, attempts = self._with_retries(fetch_video, batch_id, spec)
        acquired_at = now_iso()
        payload = {**data, "source_id": spec.source_id, "acquired_at": acquired_at}
        body = json.dumps(payload, ensure_ascii=False, indent=1).encode("utf-8")
        meta = {"acquired_at": acquired_at, "final_url": spec.canonical_url, "original_url": spec.original_url,
                "canonical_url": spec.canonical_url, "language_code": data.get("language_code"),
                "is_generated": data.get("is_generated")}
        return spec, save_to_cache(cache_root, spec.source_id, "video", body, meta), attempts

    # Extração e publicação --------------------------------------------------------

    def _extract(self, spec: SourceSpec, cached: AcquiredSource, include_comments: bool) -> ExtractedDocument:
        raw = Path(cached.body_path).read_bytes()
        if spec.kind == "article":
            html = decode_html(raw, cached.meta.get("charset"))
            return extract_article(html, cached.final_url, include_comments=include_comments,
                                   min_chars=self.config.min_chars)
        try:
            data = load_transcript(raw, spec.video_id or "")
        except ValueError as exc:
            raise SourceFailure(Status.SKIPPED, "offline_cache_miss", f"Cache de legenda inválido: {exc}.") from None
        return format_transcript(data)

    def process_source(self, raw: RawSource, batch_id: str, position: int | None, mode: str,
                       seen: set[str]) -> SourceResult:
        started = time.monotonic()
        result = SourceResult(None, raw.original_url, None, None, None, Status.FAILED.value, None, "",
                              catalog_id=raw.catalog_id)
        try:
            try:
                spec = classify(raw.original_url)
            except UrlError as exc:
                raise SourceFailure(Status.FAILED, exc.reason, str(exc)) from None
            result.source_id, result.canonical_url, result.kind = spec.source_id, spec.canonical_url, spec.kind
            if spec.canonical_url in seen:
                raise SourceFailure(Status.SKIPPED, "duplicate", "Fonte repetida neste lote.")
            seen.add(spec.canonical_url)
            include_comments = raw.include_comments if raw.include_comments is not None else self.config.include_comments
            if mode == "offline":
                self._set(batch_id, position, Status.READING_CACHE, spec, "lendo cache local")
                cached = load_cached_source(spec.source_id, self.config.cache_root)
                if cached is None:
                    raise SourceFailure(Status.SKIPPED, "offline_cache_miss", "Sem cache válido; modo offline não usa a rede.")
                result.cache_origin = cached.revision
            else:
                self._set(batch_id, position, Status.FETCHING, spec, f"buscando {redact(spec.canonical_url)}")
                spec, cached, result.attempts = self._acquire_online(spec, batch_id)
                result.source_id, result.canonical_url, result.kind = spec.source_id, spec.canonical_url, spec.kind
                result.cache_origin = cached.revision
            result.acquired_at = cached.acquired_at
            result.final_url = cached.final_url
            self._set(batch_id, position, Status.EXTRACTING, spec, "extraindo conteúdo")
            options = hashlib.sha256(json.dumps(
                {"format": FORMAT_SCHEMA, "version": __version__, "comments": include_comments,
                 "min_chars": self.config.min_chars}, sort_keys=True).encode()).hexdigest()
            name = document_name(spec)
            target = self.config.output_root / name
            existing = self.repository.document(spec.source_id)
            if (existing and existing["cache_revision"] == cached.revision and existing["options_hash"] == options
                    and sha256_file(target) == existing["sha256"]):
                result.status, result.reason_code, result.noop = Status.COMPLETED.value, "unchanged", True
                result.message = "Mesmo cache e opções: documento existente preservado."
                result.output_path, result.hash = existing["path"], existing["sha256"]
                result.extracted_at, result.language = existing["extracted_at"], existing["language"]
                return result
            document = self._extract(spec, cached, include_comments)
            extracted_at = now_iso()
            markdown = build_markdown(document, spec, extracted_at=extracted_at, acquired_at=cached.acquired_at,
                                      final_url=cached.final_url)
            expected = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
            self._set(batch_id, position, Status.WRITING, spec, f"gravando {name}")
            self.repository.begin_write(spec.source_id, str(target), expected, batch_id, position)
            try:
                stored = write_document_atomic(markdown, name, self.config.output_root)
            except SourceFailure:
                self.repository.abort_write(spec.source_id)
                raise
            self.repository.finish_write(spec.source_id, {
                "source_id": spec.source_id, "path": stored.path, "sha256": stored.sha256, "kind": spec.kind,
                "original_url": spec.original_url, "canonical_url": spec.canonical_url,
                "final_url": cached.final_url, "extracted_at": extracted_at, "acquired_at": cached.acquired_at,
                "cache_revision": cached.revision, "options_hash": options, "language": document.language,
                "body_sha256": body_hash(document.body),
            })
            result.status, result.reason_code = Status.COMPLETED.value, None
            result.message = f"Documento publicado: {name}"
            result.output_path, result.hash, result.extracted_at = stored.path, stored.sha256, extracted_at
            result.language, result.warnings = document.language, document.warnings
            return result
        except SourceFailure as exc:
            result.status, result.reason_code, result.message = exc.status.value, exc.reason, exc.message
            result.attempts = int(exc.extra.get("attempts", result.attempts))
            if exc.extra.get("retry_after_at"):
                result.warnings.append(f"retry_after_at={exc.extra['retry_after_at']}")
            return result
        except Exception as exc:  # falha de implementação: item falha, lote continua
            import logging

            logging.getLogger("rag_ingestion").exception("erro inesperado em %s", redact(raw.original_url))
            result.status, result.reason_code = Status.FAILED.value, "internal_error"
            result.message = f"Erro inesperado ({type(exc).__name__}); detalhes no log local."
            return result
        finally:
            result.duration_ms = int((time.monotonic() - started) * 1000)

    def _set(self, batch_id: str, position: int | None, status: Status, spec: SourceSpec, message: str) -> None:
        if position is not None:
            self.repository.set_item(batch_id, position, status.value)
        self.events.emit(batch_id, spec.source_id, status.value, status.value, message)

    # Lote ---------------------------------------------------------------------------

    def run_batch(self, batch_id: str) -> dict[str, Any]:
        summary = self.repository.batch(batch_id, limit=10_000)
        if summary is None:
            raise KeyError(batch_id)
        mode = summary["mode"]
        self.repository.set_batch_state(batch_id, "running")
        seen = {
            item["result"]["canonical_url"]
            for item in summary["items"]
            if item["result"] and item["status"] == "completed" and item["result"].get("canonical_url")
        }
        for row in self.repository.pending_items(batch_id):
            if self.cancel.is_set() or self.repository.cancel_requested(batch_id):
                break
            raw = RawSource(row["raw_url"], catalog_id=row["catalog_id"],
                            curation=json.loads(row["curation"]) if row["curation"] else None,
                            include_comments=None if row["include_comments"] is None else bool(row["include_comments"]))
            self.repository.set_item(batch_id, row["position"], Status.VALIDATING.value)
            result = self.process_source(raw, batch_id, row["position"], mode, seen)
            self.repository.set_item(batch_id, row["position"], result.status, result)
            self.events.emit(batch_id, result.source_id, "done", result.status,
                             f"{result.reason_code or 'ok'}: {result.message}")
        cancelled = self.cancel.is_set() or self.repository.cancel_requested(batch_id)
        if cancelled:
            for row in self.repository.pending_items(batch_id):
                self.repository.set_item(batch_id, row["position"], Status.CANCELLED.value)
        final = self.repository.batch(batch_id, limit=10_000) or summary
        state = "cancelled" if cancelled else ("completed_with_errors" if final["counts"]["failed"] else "completed")
        self.repository.set_batch_state(batch_id, state)
        final["state"] = state
        self._export_manifest(final)
        return final

    def _export_manifest(self, report: dict[str, Any]) -> None:
        try:
            self.config.manifests_root.mkdir(parents=True, exist_ok=True)
            path = self.config.manifests_root / f"{report['id']}.json"
            payload = {"schema": "rag-ingestion-report/v1", "format_schema": FORMAT_SCHEMA,
                       "tool": f"rag_ingestion {__version__}", **report}
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(path)
            report["manifest_path"] = str(path)
        except OSError:
            report.setdefault("warnings", []).append("Falha ao exportar o manifesto; documentos confirmados seguem válidos.")
