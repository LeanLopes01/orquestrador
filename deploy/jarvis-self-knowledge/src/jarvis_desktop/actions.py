"""Actions the server may ask this PC to run. Parameters are validated here, and
subprocesses get argument lists, never shell strings built from spoken text."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from typing import Any

import aiohttp

from .agent_jobs import JobManager
from .browser_open import BrowserOpenError, open_on_pc
from .capture import CaptureError, capture_available, capture_vscode
from .coding import activity_report
from .orchestrator_runtime import runtime_status
from .rag_service import RagStack
from .remote_control import RemoteControlError
from .remote_control import start as start_remote_control
from .snapshot import snapshot
from .system_inspection import inspect_system
from .usage import usage_report
from .workspaces import WorkspaceError

if __package__ and __package__.startswith("src."):
    from ..spotify_cli import TARGETS, SpotifyCli, SpotifyError
else:
    from spotify_cli import TARGETS, SpotifyCli, SpotifyError

Handler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]

SPOTIFY_KINDS = {"track", "artist", "album", "playlist"}
SPOTIFY_CONTROLS = {"pause", "resume", "next", "previous"}


class ActionError(Exception):
    """A failure reported back to the server as the action's error message."""


async def ping(params: dict[str, Any]) -> dict[str, Any]:
    return {"pong": True}


def spotify_actions(cli: SpotifyCli) -> dict[str, Handler]:
    async def play(params: dict[str, Any]) -> dict[str, Any]:
        query = str(params.get("query", "")).strip()[:200]
        kind = str(params.get("kind", "track"))
        device = str(params.get("device", "computer"))
        if not query or kind not in SPOTIFY_KINDS or device not in TARGETS:
            raise ActionError("Invalid Spotify search.")
        try:
            return {"item": await cli.play_search(query, kind, device)}
        except SpotifyError as exc:
            raise ActionError(str(exc)) from exc

    def target(params: dict[str, Any]) -> str | None:
        """The device a control must act on; None (older servers) keeps the
        active device."""
        device = params.get("device")
        if device is None:
            return None
        if device not in TARGETS:
            raise ActionError("Invalid Spotify device.")
        return str(device)

    async def control(params: dict[str, Any]) -> dict[str, Any]:
        action = str(params.get("action", ""))
        if action not in SPOTIFY_CONTROLS:
            raise ActionError("Invalid Spotify control.")
        try:
            return await cli.control(action, target(params)) or {}
        except SpotifyError as exc:
            raise ActionError(str(exc)) from exc

    async def volume(params: dict[str, Any]) -> dict[str, Any]:
        try:
            level = min(1.0, max(0.0, float(params.get("level", -1))))
        except (TypeError, ValueError):
            raise ActionError("Invalid volume.") from None
        try:
            return await cli.set_volume(level, target(params)) or {}
        except SpotifyError as exc:
            raise ActionError(str(exc)) from exc

    async def now_playing(params: dict[str, Any]) -> dict[str, Any]:
        try:
            state = await cli.playback_state()
        except SpotifyError as exc:
            raise ActionError(str(exc)) from exc
        state.pop("device_id", None)
        return state

    async def status(params: dict[str, Any]) -> dict[str, Any]:
        try:
            state = await cli.status()
        except SpotifyError as exc:
            raise ActionError(str(exc)) from exc
        return {
            "running": bool(state.get("running")),
            "logged_in": bool(state.get("logged_in")),
        }

    return {
        "spotify.play": play,
        "spotify.control": control,
        "spotify.volume": volume,
        "spotify.status": status,
        "spotify.now_playing": now_playing,
    }


async def coding_activity(params: dict[str, Any]) -> dict[str, Any]:
    agent = str(params.get("agent", "all"))
    if agent not in {"all", "claude", "codex", "antigravity"}:
        raise ActionError("Unknown coding agent.")
    try:
        hours = float(params.get("hours", 12))
        limit = int(params.get("limit", 5))
    except (TypeError, ValueError):
        raise ActionError("Invalid report window.") from None
    # Reading session logs is file I/O; keep the connection's event loop free.
    return await asyncio.to_thread(
        activity_report, agent=agent, hours=hours, limit=limit
    )


async def vscode_capture(params: dict[str, Any]) -> dict[str, Any]:
    hint = str(params.get("window", ""))[:100]
    try:
        return await asyncio.to_thread(capture_vscode, hint)
    except CaptureError as exc:
        raise ActionError(str(exc)) from exc


async def coding_usage(params: dict[str, Any]) -> dict[str, Any]:
    return await asyncio.to_thread(usage_report)


async def claude_remote_control(params: dict[str, Any]) -> dict[str, Any]:
    chat = str(params.get("chat", ""))[:120]
    try:
        return await asyncio.to_thread(start_remote_control, chat)
    except RemoteControlError as exc:
        raise ActionError(str(exc)) from exc


async def browser_open(params: dict[str, Any]) -> dict[str, Any]:
    what = str(params.get("what", ""))[:500]
    try:
        return await asyncio.to_thread(open_on_pc, what)
    except BrowserOpenError as exc:
        raise ActionError(str(exc)) from exc


async def diagnostics_snapshot(params: dict[str, Any]) -> dict[str, Any]:
    try:
        since = float(params.get("since") or 0)
    except (TypeError, ValueError):
        raise ActionError("Invalid period.") from None
    return await asyncio.to_thread(snapshot, since)


def orchestrator_actions(
    jobs: JobManager, *, require_runtime: bool = False
) -> dict[str, Handler]:
    """Jobs of the coding agents for the JARVIS orchestrator (see agent_jobs.py)."""

    async def start(params: dict[str, Any]) -> dict[str, Any]:
        if require_runtime and not (await runtime_status()).get("online"):
            raise ActionError(
                "Orquestrador local desligado. Abra o aplicativo no PC principal."
            )
        try:
            return jobs.start(params)
        except WorkspaceError as exc:
            raise ActionError(str(exc)) from exc

    async def cancel(params: dict[str, Any]) -> dict[str, Any]:
        return await jobs.cancel(str(params.get("job_id", "")))

    async def status(params: dict[str, Any]) -> dict[str, Any]:
        return {"jobs": jobs.status([str(j) for j in params.get("job_ids") or []])}

    async def apply(params: dict[str, Any]) -> dict[str, Any]:
        try:
            return await asyncio.to_thread(jobs.apply, params)
        except WorkspaceError as exc:
            raise ActionError(str(exc)) from exc

    return {
        "orchestrator.runtime": runtime_status,
        "orchestrator.start": start,
        "orchestrator.cancel": cancel,
        "orchestrator.status": status,
        "orchestrator.apply": apply,
    }


RAG_SCOPES = {"code", "documents", "all"}
RAG_TEXT_LIMIT = 20_000


def rag_actions(stack: RagStack) -> dict[str, Handler]:
    """The DiceVTT RAG on this PC (see rag_service.py), for Projects on the phones and
    for the voice agent. Only fixed routes of the local service; no paths from callers."""

    async def call(
        method: str, path: str, body: dict[str, Any] | None = None, timeout: float = 30
    ) -> dict[str, Any]:
        try:
            status, data = await stack.request(
                "rag", method, path, body, timeout=timeout
            )
        except (aiohttp.ClientError, TimeoutError, ValueError, OSError):
            raise ActionError(
                "O RAG local não está respondendo. Ligue o helper no PC principal (iniciar-tudo.cmd)."
            ) from None
        if status >= 400:
            raise ActionError(
                str(data.get("message") or f"O RAG respondeu HTTP {status}.")
            )
        return data

    def query_of(params: dict[str, Any]) -> str:
        query = str(params.get("query", "")).strip()
        if not query or len(query) > 2000:
            raise ActionError("Envie uma pergunta de até 2000 caracteres.")
        return query

    def ask_id(params: dict[str, Any]) -> str:
        value = str(params.get("ask_id", ""))
        if not value.isalnum() or len(value) > 64:
            raise ActionError("Pedido inválido.")
        return value

    async def health(params: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {"online": False, "services": stack.status()}
        with contextlib.suppress(ActionError):
            data = await call("GET", "/v1/rag/health", timeout=5)
            result.update(
                online=True,
                rag={
                    k: data.get(k)
                    for k in (
                        "starting",
                        "startup_error",
                        "embeddings",
                        "index",
                        "watcher",
                        "model",
                        "roots",
                        "version",
                    )
                },
            )
        try:
            status, data = await stack.request(
                "ingestion", "GET", "/v1/ingestion/health", timeout=5
            )
            result["ingestion"] = {
                "online": status == 200,
                "running_batch": data.get("running_batch"),
            }
        except (aiohttp.ClientError, TimeoutError, ValueError, OSError):
            result["ingestion"] = {"online": False}
        return result

    async def retrieve(params: dict[str, Any]) -> dict[str, Any]:
        try:
            limit = min(max(int(params.get("text_limit") or 6000), 200), RAG_TEXT_LIMIT)
        except (TypeError, ValueError):
            raise ActionError("Limite de texto inválido.") from None
        return await call(
            "POST",
            "/v1/rag/retrieve",
            {"project_id": "dicevtt", "query": query_of(params), "text_limit": limit},
            timeout=60,
        )

    async def ask(params: dict[str, Any]) -> dict[str, Any]:
        request_id = str(params.get("request_id") or "")[:80] or None
        return await call(
            "POST",
            "/v1/rag/asks",
            {
                "project_id": "dicevtt",
                "query": query_of(params),
                "request_id": request_id,
            },
        )

    async def ask_status(params: dict[str, Any]) -> dict[str, Any]:
        return await call("GET", f"/v1/rag/asks/{ask_id(params)}")

    async def ask_cancel(params: dict[str, Any]) -> dict[str, Any]:
        return await call("POST", f"/v1/rag/asks/{ask_id(params)}/cancel", {})

    async def index(params: dict[str, Any]) -> dict[str, Any]:
        scope = str(params.get("scope", "all"))
        if scope not in RAG_SCOPES:
            raise ActionError("Escopo inválido: use code, documents ou all.")
        return await call(
            "POST", "/v1/rag/index-jobs", {"project_id": "dicevtt", "scope": scope}
        )

    async def index_status(params: dict[str, Any]) -> dict[str, Any]:
        job_id = str(params.get("job_id", ""))
        if not job_id.isalnum() or len(job_id) > 64:
            raise ActionError("Job inválido.")
        return await call("GET", f"/v1/rag/index-jobs/{job_id}")

    return {
        "rag.health": health,
        "rag.retrieve": retrieve,
        "rag.ask": ask,
        "rag.ask_status": ask_status,
        "rag.ask_cancel": ask_cancel,
        "rag.index": index,
        "rag.index_status": index_status,
    }


def build_actions(
    jobs: JobManager | None = None, rag: RagStack | None = None
) -> dict[str, Handler]:
    actions: dict[str, Handler] = {
        "desktop.ping": ping,
        "system.inspect": inspect_system,
        "coding.activity": coding_activity,
        "coding.usage": coding_usage,
        "claude.remote_control": claude_remote_control,
        "browser.open": browser_open,
        "diagnostics.snapshot": diagnostics_snapshot,
    }
    if capture_available():
        actions["vscode.capture"] = vscode_capture
    cli = SpotifyCli()
    if cli.available:
        actions.update(spotify_actions(cli))
    if jobs is not None:
        import platform

        if platform.node().casefold() == "batcomputador":
            actions.update(orchestrator_actions(jobs, require_runtime=True))
    if rag is not None and rag.available:
        actions.update(rag_actions(rag))
    return actions
