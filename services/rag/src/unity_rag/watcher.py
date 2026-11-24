"""Watchdog dos scripts. O callback só registra o evento; o trabalho vai para a fila
única do IndexWorker (um escritor do Chroma), após o debounce por caminho."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path

from .code_indexer import CodeIndexer, is_script

logger = logging.getLogger("unity_rag")
Submit = Callable[[str, Callable[[], object]], object]


class ScriptWatcher:
    def __init__(self, indexer: CodeIndexer, submit: Submit, *, debounce_ms: int = 500, queue_limit: int = 2000) -> None:
        self._indexer = indexer
        self._submit = submit
        self._debounce = debounce_ms / 1000
        self._limit = queue_limit
        self._lock = threading.Lock()
        self._pending: dict[str, tuple[float, str]] = {}
        self._reconcile = False
        self._stop = threading.Event()
        self._observer = None
        self._pump: threading.Thread | None = None
        self.state = "stopped"
        self.error: str | None = None
        self.events_seen = 0

    # Thread de eventos: só agenda -------------------------------------------------

    def record(self, kind: str, src: str, dest: str | None = None, is_directory: bool = False) -> None:
        now = time.monotonic()
        with self._lock:
            self.events_seen += 1
            if is_directory:
                if kind in {"deleted", "moved", "created"}:
                    self._reconcile = True
                return
            if kind == "moved":
                if is_script(Path(src)):
                    self._pending[src] = (now, "delete")
                if dest and is_script(Path(dest)):
                    self._pending[dest] = (now, "upsert")
            elif kind == "deleted":
                if is_script(Path(src)):
                    self._pending[src] = (now, "delete")
            elif kind in {"created", "modified", "closed"} and is_script(Path(src)):
                self._pending[src] = (now, "upsert")
            if len(self._pending) > self._limit:
                logger.warning("fila do watcher saturada (%s caminhos): reconciliação completa", len(self._pending))
                self._pending.clear()
                self._reconcile = True

    def _take_due(self) -> tuple[list[tuple[str, str]], bool]:
        now = time.monotonic()
        with self._lock:
            due = [(path, action) for path, (stamp, action) in self._pending.items() if now - stamp >= self._debounce]
            for path, _ in due:
                del self._pending[path]
            reconcile, self._reconcile = self._reconcile, False
        return due, reconcile

    def _apply(self, due: list[tuple[str, str]]) -> dict[str, int]:
        counts = {"indexed": 0, "removed": 0, "errors": 0}
        for raw, action in due:
            path = Path(raw)
            if action == "delete" or not path.exists():
                if self._indexer.remove_path(path):
                    counts["removed"] += 1
                continue
            if not self._indexer.in_scope(path):
                continue
            outcome = self._indexer.index_file(path)
            if outcome.startswith("error:"):
                counts["errors"] += 1
                # arquivo parcial/bloqueado: nova tentativa no próximo ciclo
                with self._lock:
                    self._pending.setdefault(raw, (time.monotonic() + 1.0, "upsert"))
            else:
                counts["indexed"] += 1
        if any(counts.values()):
            logger.debug("watcher: %s", counts)
        return counts

    def _loop(self) -> None:
        while not self._stop.wait(0.1):
            due, reconcile = self._take_due()
            if reconcile:
                self._submit("watcher-reconcile", self._indexer.reconcile)
            if due:
                self._submit("watcher-batch", lambda due=due: self._apply(due))

    # Ciclo de vida -----------------------------------------------------------------

    def start(self) -> None:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        watcher = self

        class Handler(FileSystemEventHandler):
            def on_any_event(self, event) -> None:  # type: ignore[override]
                if event.event_type in {"opened", "closed_no_write"}:
                    return
                dest = getattr(event, "dest_path", None)
                watcher.record(event.event_type, str(event.src_path), str(dest) if dest else None, event.is_directory)

        root = self._indexer.root
        if not root.is_dir():
            self.state, self.error = "error", f"Raiz de scripts inacessível: {root}"
            return
        observer = Observer()
        observer.schedule(Handler(), str(root), recursive=True)
        observer.daemon = True
        observer.start()
        self._observer = observer
        self._pump = threading.Thread(target=self._loop, name="rag-watcher", daemon=True)
        self._pump.start()
        self.state = "running"

    def stop(self) -> None:
        self._stop.set()
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
        if self._pump is not None:
            self._pump.join(timeout=5)
        self.state = "stopped"
