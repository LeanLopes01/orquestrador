"""Logs estruturados (JSONL local) e eventos de progresso. URLs com query são redigidas."""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable
from pathlib import Path

from .acquisition import now_iso
from .models import ProgressEvent

logger = logging.getLogger("rag_ingestion")
Listener = Callable[[ProgressEvent], None]


class EventLog:
    def __init__(self, path: Path | None, listener: Listener | None = None) -> None:
        self._path = path
        self._listener = listener
        self._lock = threading.Lock()
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, batch_id: str, source_id: str | None, stage: str, status: str, message: str) -> None:
        event = ProgressEvent(batch_id, source_id, stage, status, now_iso(), message)
        if self._path is not None:
            try:
                with self._lock, open(self._path, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
            except OSError:
                logger.warning("não foi possível gravar o log de eventos")
        if self._listener is not None:
            self._listener(event)
