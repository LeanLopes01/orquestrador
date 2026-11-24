"""RagOrchestrator: start(), retrieve(), ask(), close(). Sem acoplamento a HTTP/UI.

Threads: um IndexWorker serializa toda escrita no Chroma (watcher, jobs, reindex de
ponteiros desatualizados); um executor de um worker serializa carregamento e geração
do AirLLM. retrieve() roda na thread chamadora e continua disponível durante a geração.
"""

from __future__ import annotations

import hashlib
import logging
import queue
import threading
import time
import uuid
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from .config import RagConfig, apply_offline_environment
from .context_builder import SourceTooLarge, build_context
from .models import AnswerResult, IndexReport, ProgressEvent, RetrievalResult

logger = logging.getLogger("unity_rag")


class CapabilityUnavailable(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class IndexWorker:
    def __init__(self) -> None:
        self._queue: queue.Queue[tuple[str, Callable[[], Any], Future] | None] = queue.Queue()
        self._thread = threading.Thread(target=self._loop, name="rag-index-writer", daemon=True)
        self.current: str | None = None

    def start(self) -> None:
        self._thread.start()

    def submit(self, label: str, work: Callable[[], Any]) -> Future:
        future: Future = Future()
        self._queue.put((label, work, future))
        return future

    def pending(self) -> int:
        return self._queue.qsize()

    def _loop(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                return
            label, work, future = item
            if not future.set_running_or_notify_cancel():
                continue
            self.current = label
            try:
                future.set_result(work())
            except BaseException as exc:  # noqa: BLE001 - devolvido ao chamador
                logger.exception("tarefa de índice %s falhou", label)
                future.set_exception(exc)
            finally:
                self.current = None

    def stop(self, timeout: float = 30) -> None:
        self._queue.put(None)
        if self._thread.is_alive():
            self._thread.join(timeout=timeout)


class RagOrchestrator:
    def __init__(self, config: RagConfig, *, embedder=None, generator=None, watch: bool | None = None) -> None:
        self.config = config
        self._embedder = embedder
        self._generator = generator
        self._watch = config.watcher.enabled if watch is None else watch
        self.embeddings_state = "unloaded"
        self.embeddings_error: str | None = None
        self.started = threading.Event()
        self.state = None
        self.store = None
        self.code = None
        self.docs = None
        self.retriever = None
        self.watcher = None
        self.worker = IndexWorker()
        self._gen = ThreadPoolExecutor(max_workers=1, thread_name_prefix="rag-generator")
        self._reindex_pending: set[str] = set()
        self._reindex_lock = threading.Lock()
        self.last_reports: dict[str, dict] = {}

    # Ciclo de vida -----------------------------------------------------------------

    def start(self) -> None:
        apply_offline_environment(self.config)
        from .airllm_engine import AirLlmEngine, GeneratorUnavailable
        from .code_indexer import CodeIndexer
        from .document_indexer import DocumentIndexer
        from .index_state import IndexState
        from .retrieval import Retriever
        from .store import VectorStore

        self.state = IndexState(self.config.index_state_path)
        self.state.interrupt_running()
        if self._generator is None:
            self._generator = AirLlmEngine(self.config.generator)
            if self._generator.state == "unloaded":
                try:
                    self._generator.check()  # só existência de arquivos; não carrega pesos
                except GeneratorUnavailable as exc:
                    logger.warning("gerador indisponível: %s", exc)
        self.embeddings_state = "loading"
        try:
            if self._embedder is None:
                from .embeddings import SentenceTransformerEmbedder

                self._embedder = SentenceTransformerEmbedder(self.config.embedding)
        except Exception as exc:
            self.embeddings_state, self.embeddings_error = "error", str(exc)
            logger.error("embeddings indisponíveis: %s", exc)
            self.started.set()
            return
        self.embeddings_state = "ready"
        self.store = VectorStore(self.config.chroma_path, self._embedder.signature)
        self.code = CodeIndexer(self.config, self._embedder, self.store, self.state)
        self.docs = DocumentIndexer(self.config, self._embedder, self.store, self.state)
        self.retriever = Retriever(self.config, self._embedder, self.store, self.code,
                                   lambda: self.docs.recovering, self.schedule_reindex)
        self.worker.start()
        # Documentos dirty de uma queda anterior são reconciliados antes de liberar a busca.
        self.worker.submit("documents-recovery", self._record("documents-recovery", self.docs.recover)).result()
        if self._watch:
            from .watcher import ScriptWatcher

            # Observa antes de varrer: mudanças durante o scan ficam na fila do watcher.
            self.watcher = ScriptWatcher(self.code, self.worker.submit, debounce_ms=self.config.watcher.debounce_ms,
                                         queue_limit=self.config.watcher.queue_limit)
            self.watcher.start()
            self.worker.submit("code-reconcile", self._record("code", self.code.reconcile))
        self.started.set()

    def _record(self, name: str, work: Callable[[], IndexReport]) -> Callable[[], IndexReport]:
        def run() -> IndexReport:
            report = work()
            self.last_reports[name] = {**report.to_dict(), "finished_at": time.time()}
            return report

        return run

    def close(self) -> None:
        if self.watcher is not None:
            self.watcher.stop()
        self._gen.shutdown(wait=True, cancel_futures=True)
        if self.state is not None:
            self.worker.stop()
            self.state.close()

    # Índice ---------------------------------------------------------------------------

    def _require_index(self) -> None:
        if not self.started.is_set():
            raise CapabilityUnavailable("starting", "O RAG ainda está iniciando.")
        if self.embeddings_state != "ready":
            raise CapabilityUnavailable("embeddings_unavailable", self.embeddings_error or "Embeddings indisponíveis.")

    def schedule_reindex(self, path: Path) -> None:
        key = str(path)
        with self._reindex_lock:
            if key in self._reindex_pending:
                return
            self._reindex_pending.add(key)

        def run() -> str:
            with self._reindex_lock:
                self._reindex_pending.discard(key)
            return self.code.index_file(path) if path.exists() else str(self.code.remove_path(path))

        self.worker.submit(f"reindex {path.name}", run)

    def submit_index(self, scope: str) -> Future:
        self._require_index()
        if scope not in {"code", "documents", "all"}:
            raise ValueError("scope deve ser code, documents ou all")

        def run() -> dict[str, Any]:
            reports = {}
            if scope in {"code", "all"}:
                reports["code"] = self._record("code", self.code.reconcile)().to_dict()
            if scope in {"documents", "all"}:
                reports["documents"] = self._record("documents", self.docs.index_documents)().to_dict()
            return reports

        return self.worker.submit(f"index-{scope}", run)

    # Consulta ---------------------------------------------------------------------------

    def retrieve(self, query: str) -> RetrievalResult:
        self._require_index()
        return self.retriever.retrieve(query)

    def ask(self, query: str, on_progress: Callable[[ProgressEvent], None] | None = None, *,
            cancel: threading.Event | None = None, request_id: str | None = None) -> AnswerResult:
        from .airllm_engine import GeneratorUnavailable
        from .progress import Progress

        self._require_index()
        cancel = cancel or threading.Event()
        generator = self._generator
        try:
            generator.check()
            tokenizer = generator.tokenizer()
        except GeneratorUnavailable as exc:
            raise CapabilityUnavailable(exc.code, str(exc)) from None
        with Progress(request_id or uuid.uuid4().hex, on_progress) as progress:
            retrieval = self.retriever.retrieve(query)
            progress.stage("reading", f"{len(retrieval.files_read)} scripts lidos do disco")
            progress.stage("context")
            try:
                bundle = build_context(query, retrieval, tokenizer, max_seq_len=self.config.generator.max_seq_len,
                                       max_new_tokens=self.config.generator.max_new_tokens)
            except SourceTooLarge as exc:
                raise CapabilityUnavailable("query_too_large", str(exc)) from None
            if generator.state != "ready":
                progress.stage("loading")
                try:
                    generator.load()
                except GeneratorUnavailable as exc:
                    raise CapabilityUnavailable(exc.code, str(exc)) from None
            progress.stage("generating")
            answer, generated = generator.generate(
                bundle.prompt, max_new_tokens=self.config.generator.max_new_tokens, cancel=cancel,
                on_token=lambda n: progress.detail(f"{n} tokens gerados"),
            )
            progress.stage("done")
        included = {item["id"] for item in bundle.included}
        sources = [
            {**s.to_dict(text_limit=4000), "included": s.id in included,
             "scope": next((i["scope"] for i in bundle.included if i["id"] == s.id), "omitted")}
            for s in retrieval.sources
        ]
        warnings = list(dict.fromkeys([*retrieval.warnings, *bundle.warnings]))
        # Arquivos alterados entre a leitura e a entrega são avisados.
        for source in retrieval.sources:
            if source.kind == "code_pointer" and source.id in included:
                try:
                    if hashlib.sha256(Path(source.filepath).read_bytes()).hexdigest() != source.hash:
                        warnings.append(f"source_changed_after_read: {source.relpath} mudou depois da leitura.")
                except OSError:
                    warnings.append(f"source_changed_after_read: {source.relpath} sumiu depois da leitura.")
        timings = {**retrieval.timings_ms, **progress.timings}
        return AnswerResult(answer, sources, warnings, timings, generator.model_name, bundle.token_count, generated)

    def ask_async(self, query: str, on_progress=None, *, cancel: threading.Event | None = None,
                  request_id: str | None = None) -> Future:
        return self._gen.submit(self.ask, query, on_progress, cancel=cancel, request_id=request_id)

    # Saúde --------------------------------------------------------------------------------

    def health(self) -> dict[str, Any]:
        index: dict[str, Any] = {"state": "unavailable"}
        if self.store is not None and self.state is not None:
            dirty = self.docs.recovering
            index = {
                "state": "ready" if not dirty else "documents_recovering",
                "code_pointers": self.store.count(self.config.project_id, "code_pointer"),
                "document_chunks": self.store.count(self.config.project_id, "documentation"),
                "documents": len([d for d in self.state.documents() if d["state"] == "clean"]),
                "writer": self.worker.current, "queued_tasks": self.worker.pending(),
                "last_reports": self.last_reports, "collection": self.store.name,
            }
        generator = self._generator
        return {
            "embeddings": {"state": self.embeddings_state, "model": getattr(self._embedder, "name", self.config.embedding.repo_id),
                           "error": self.embeddings_error},
            "index": index,
            "watcher": {"state": self.watcher.state if self.watcher else ("disabled" if not self._watch else "stopped"),
                        "error": self.watcher.error if self.watcher else None,
                        "events_seen": self.watcher.events_seen if self.watcher else 0},
            "model": {"state": generator.state if generator else "not_configured",
                      "reason": generator.reason if generator else None,
                      "name": generator.model_name if generator else None,
                      "device": self.config.generator.device, "max_new_tokens": self.config.generator.max_new_tokens},
            "roots": {"scripts": str(self.config.scripts_root), "docs": str(self.config.docs_root),
                      "scripts_available": self.config.scripts_root.is_dir(),
                      "docs_available": self.config.docs_root.is_dir()},
        }
