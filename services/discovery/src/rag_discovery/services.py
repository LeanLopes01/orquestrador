"""Clientes dos serviços locais (ingestão 8766, RAG 8767) com o token local de cada um.

A descoberta não escreve documentos nem abre o Chroma: entrega URLs à ingestão e pede a
indexação ao RAG, pelos mesmos endpoints da UI.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

BATCH_DONE = {"completed", "completed_with_errors", "cancelled", "interrupted"}
JOB_DONE = {"completed", "failed", "cancelled", "interrupted"}


class ServiceError(Exception):
    pass


class LocalService:
    def __init__(self, name: str, host: str, port: int, token_path: Path) -> None:
        self.name = name
        self.base = f"http://{host}:{port}"
        self._token_path = token_path

    def call(self, method: str, path: str, body: dict | None = None, timeout: float = 30) -> dict[str, Any]:
        try:
            token = self._token_path.read_text(encoding="ascii").strip()
        except OSError:
            raise ServiceError(f"{self.name}: token local ausente em {self._token_path}.") from None
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method,
                                         headers={"x-local-token": token, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as exc:
            try:
                message = json.loads(exc.read()).get("message", "")
            except ValueError:
                message = ""
            raise ServiceError(f"{self.name}: HTTP {exc.code} {message}".strip()) from None
        except (urllib.error.URLError, OSError) as exc:
            raise ServiceError(
                f"{self.name} offline em {self.base} ({exc}). Ligue com iniciar-tudo.cmd."
            ) from None

    def online(self, health_path: str) -> bool:
        try:
            return bool(self.call("GET", health_path, timeout=5).get("online"))
        except ServiceError:
            return False


def wait_until(fetch: Callable[[], dict[str, Any]], done: set[str], *, poll: float, timeout: float,
               on_poll: Callable[[dict[str, Any]], None] | None = None,
               sleep: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while True:
        state = fetch()
        if on_poll:
            on_poll(state)
        if state.get("state") in done:
            return state
        if time.monotonic() > deadline:
            raise ServiceError(f"tempo esgotado aguardando (último estado: {state.get('state')}).")
        sleep(poll)
