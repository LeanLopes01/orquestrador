"""Estados reais de progresso com heartbeat de tempo decorrido (sem % nem ETA inventados)."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from .models import ProgressEvent

STAGES = {
    "embeddings": "Processando embeddings...",
    "reading": "Lendo arquivos locais...",
    "context": "Montando contexto...",
    "loading": "Carregando modelo...",
    "generating": "Gerando resposta...",
    "done": "Concluído.",
}
Listener = Callable[[ProgressEvent], None]


class Progress:
    def __init__(self, request_id: str, listener: Listener | None, heartbeat_seconds: float = 3.0) -> None:
        self.request_id = request_id
        self._listener = listener
        self._started = time.monotonic()
        self._stage = "embeddings"
        self._detail = ""
        self._interval = heartbeat_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.timings: dict[str, int] = {}
        self._stage_started = self._started

    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self._started) * 1000)

    def _emit(self) -> None:
        if self._listener is not None:
            message = STAGES.get(self._stage, self._stage) + (f" {self._detail}" if self._detail else "")
            self._listener(ProgressEvent(self.request_id, self._stage, message, self.elapsed_ms()))

    def stage(self, name: str, detail: str = "") -> None:
        now = time.monotonic()
        self.timings[self._stage] = self.timings.get(self._stage, 0) + int((now - self._stage_started) * 1000)
        self._stage, self._detail, self._stage_started = name, detail, now
        self._emit()

    def detail(self, text: str) -> None:
        self._detail = text

    def __enter__(self) -> Progress:
        self._emit()
        self._thread = threading.Thread(target=self._beat, name=f"heartbeat-{self.request_id[:8]}", daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._stop.set()
        now = time.monotonic()
        self.timings[self._stage] = self.timings.get(self._stage, 0) + int((now - self._stage_started) * 1000)
        self.timings["total"] = self.elapsed_ms()

    def _beat(self) -> None:
        while not self._stop.wait(self._interval):
            self._emit()
