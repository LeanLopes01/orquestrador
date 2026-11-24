"""HTTP surface of jarvis-control.

public app   (127.0.0.1:8090, published by the Cloudflare tunnel): pairing, sessions
             for the phone app, the master phone's events, reports and commands,
             and the WebSocket for the Windows helper.
internal app (127.0.0.1:8091, never tunnelled): the agent asks for desktop actions
             and, through the personal gateway, for read-only personal data.
"""

from __future__ import annotations

import asyncio
import contextlib
import hmac
import json
import logging
import re
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from typing import Any

from aiohttp import WSMsgType, web

from .backends import LiveKitRooms
from .browser import COOKIE, browser_surface
from .commands import CommandRunner
from .desktop import DesktopHub, DesktopOfflineError, DesktopTimeoutError
from .diagnostics import Diagnostics
from .extensions import Catalog
from .extensions import routes as catalog_routes
from .integrations import IntegrationError
from .orchestrator import Orchestrator, OrchestratorError
from .personal import Call, InvalidArgumentsError, PersonalDeniedError, PersonalGateway
from .releases import routes as release_routes
from .routines import RoutineError
from .routines import validate as validate_routine
from .sessions import BusyError, NotFoundError, SessionManager
from .store import DELIVERY_STAGES, Device, Session, Store

logger = logging.getLogger("jarvis_control")

Handler = Callable[[web.Request], Awaitable[web.StreamResponse]]
DEVICE_KEY = web.RequestKey("device", Device)
PAIR_LIMIT = (10, 900.0)  # attempts per client IP per 15 minutes
AUTH_FAILURE_LIMIT = (20, 900.0)
REQUEST_LIMIT = (300, 60.0)
STREAM_RECHECK_SECONDS = 30.0  # revalidate a long event stream's credential
COMMAND_TEXT_LIMIT = 500
SOCIAL_APPS = {"whatsapp", "instagram"}


def error(status: int, code: str, message: str) -> web.Response:
    return web.json_response({"error": code, "message": message}, status=status)


def client_ip(request: web.Request) -> str:
    peer = request.remote or "unknown"
    # Requests through the tunnel arrive from cloudflared on localhost.
    if peer in {"127.0.0.1", "::1"}:
        return request.headers.get("CF-Connecting-IP", peer)
    return peer


class RateLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str, limit: int, window: float) -> bool:
        """Record a hit; False when the key is over its limit."""
        now = self._clock()
        hits = self._hits[key]
        while hits and hits[0] <= now - window:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True

    def over(self, key: str, limit: int, window: float) -> bool:
        now = self._clock()
        hits = self._hits[key]
        while hits and hits[0] <= now - window:
            hits.popleft()
        return len(hits) >= limit


def _bearer(request: web.Request) -> str:
    header = request.headers.get("Authorization", "")
    return (
        header[7:].strip()
        if header.startswith("Bearer ")
        else request.cookies.get(COOKIE, "")
    )


async def _optional_json(request: web.Request) -> dict[str, Any]:
    if not request.can_read_body:
        return {}
    try:
        body = await request.json()
    except ValueError:
        raise RoutineError("Send a JSON body.") from None
    return body if isinstance(body, dict) else {}


def session_context(
    body: dict[str, Any], store: Store, device_id: str | None = None
) -> dict[str, Any] | None:
    """What the agent should know for this session: a routine, where the phone is,
    the master phone's rules, and a command already transcribed on the phone."""
    context: dict[str, Any] = {}
    if device_id is not None:
        target = store.master_music_target(device_id)
        if target is not None:
            context["profile"] = {"master": True, "music_target": target}
    command = body.get("command")
    if command is not None:
        text = str(command.get("text", "") if isinstance(command, dict) else "").strip()
        if not text:
            raise RoutineError("command needs the transcribed text.")
        context["command"] = {"text": text[:COMMAND_TEXT_LIMIT]}
    if body.get("audio") is False or command is not None:
        # The phone joins without publishing its microphone.
        context["audio_input"] = False
    routine_id = body.get("routine_id")
    if routine_id:
        routine = store.routine(str(routine_id))
        if routine is None:
            raise RoutineError("Unknown routine.")
        context["routine"] = {
            k: routine[k] for k in ("id", "name", "prompt", "location")
        }
    location = body.get("location")
    if isinstance(location, dict):
        try:
            lat, lon = float(location["lat"]), float(location["lon"])
        except (KeyError, TypeError, ValueError):
            raise RoutineError("location needs numeric lat and lon.") from None
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            context["location"] = {"lat": round(lat, 3), "lon": round(lon, 3)}
    return context or None


def session_view(session: Session) -> dict[str, Any]:
    return {
        "id": session.id,
        "state": session.state,
        "room": session.room,
        "created_at": session.created_at,
        "end_reason": session.end_reason,
    }


def build_public_app(
    *,
    store: Store,
    manager: SessionManager,
    hub: DesktopHub,
    rooms: LiveKitRooms,
    unit_state: Callable[[], Awaitable[str]],
    maintenance: Callable[[], bool],
    version: str,
    limiter: RateLimiter | None = None,
    commands: CommandRunner | None = None,
    diagnostics: Diagnostics | None = None,
    extra_routes: list[web.RouteDef] | None = None,
    orchestrator: Orchestrator | None = None,
) -> web.Application:
    limiter = limiter or RateLimiter()
    commands = commands or CommandRunner(store, hub)
    operations = commands.operations
    reports_service = diagnostics  # a handler below is also called "diagnostics"

    def require(
        kind: str, *, master: bool = False, work: bool = False, personal: bool = False
    ) -> Callable[[Handler], Handler]:
        def decorator(handler: Handler) -> Handler:
            async def wrapped(request: web.Request) -> web.StreamResponse:
                ip = client_ip(request)
                if limiter.over(f"authfail:{ip}", *AUTH_FAILURE_LIMIT):
                    return error(429, "rate_limited", "Too many failed attempts.")
                device = store.device_for_token(_bearer(request), time.time())
                if device is None or (
                    device.kind not in {"app", "desktop"}
                    if kind == "work"
                    else device.kind != kind
                ):
                    limiter.hit(f"authfail:{ip}", *AUTH_FAILURE_LIMIT)
                    return error(401, "unauthorized", "Pair this device again.")
                if master and not store.profile(device.id).master:
                    return error(
                        403,
                        "not_master",
                        "Only the master phone receives reports. On the server, run"
                        " jarvis-control master DEVICE_ID.",
                    )
                request[DEVICE_KEY] = device
                if personal and not store.can_personal(device.id):
                    return error(
                        403,
                        "personal_access_required",
                        "O acesso às conexões pessoais ainda não foi liberado para este aparelho.",
                    )
                if work and not store.can_work(device.id):
                    return error(
                        403,
                        "work_access_required",
                        "This device needs reports/projects access: jarvis-control work DEVICE_ID.",
                    )
                return await handler(request)

            return wrapped

        return decorator

    @web.middleware
    async def limit_requests(
        request: web.Request, handler: Handler
    ) -> web.StreamResponse:
        if not limiter.hit(f"req:{client_ip(request)}", *REQUEST_LIMIT):
            return error(429, "rate_limited", "Too many requests.")
        return await handler(request)

    async def health(request: web.Request) -> web.Response:
        return web.json_response({"ok": True})

    @require("work", personal=True)
    async def personal_connections(request: web.Request) -> web.Response:
        return web.json_response(
            store.integrations.view(), headers={"Cache-Control": "no-store"}
        )

    @require("work", personal=True)
    async def update_personal_connection(request: web.Request) -> web.Response:
        try:
            body = await request.json()
            result = store.integrations.update(request.match_info["account_id"], body)
        except IntegrationError as exc:
            return error(exc.status, exc.code, str(exc))
        except (ValueError, TypeError):
            return error(400, "bad_request", "Envie um objeto JSON válido.")
        return web.json_response(result, headers={"Cache-Control": "no-store"})

    async def pair(request: web.Request) -> web.Response:
        if not limiter.hit(f"pair:{client_ip(request)}", *PAIR_LIMIT):
            return error(429, "rate_limited", "Too many pairing attempts.")
        try:
            body = await request.json()
            code = str(body["code"])
            name = str(body.get("name") or "device").strip() or "device"
        except (ValueError, KeyError, TypeError):
            return error(400, "bad_request", "Send a JSON body with a code.")
        redeemed = store.redeem_pairing_code(code, name, time.time())
        if redeemed is None:
            return error(400, "invalid_code", "The pairing code is wrong or expired.")
        device, token = redeemed
        logger.info("paired %s device %s (%s)", device.kind, device.id[:8], device.name)
        return web.json_response(
            {"device_id": device.id, "kind": device.kind, "device_token": token},
            status=201,
        )

    def with_connection(session: Session, device: Device) -> dict[str, Any]:
        view = session_view(session)
        if session.state in {"ready", "active"}:
            view["connection"] = {
                "server_url": rooms.url,
                "participant_token": rooms.token(
                    session.room, f"app-{device.id[:8]}", device.name
                ),
                "room_name": session.room,
            }
        return view

    @require("app")
    async def create_session(request: web.Request) -> web.Response:
        if maintenance():
            return error(503, "maintenance", "JARVIS is being updated. Try again soon.")
        device = request[DEVICE_KEY]
        key = request.headers.get("Idempotency-Key", "").strip()[:100] or None
        try:
            context = session_context(await _optional_json(request), store, device.id)
        except RoutineError as exc:
            return error(400, "bad_request", str(exc))
        try:
            session = await manager.create(device.id, key, context)
        except BusyError:
            return error(409, "busy", "JARVIS is already in a call on another device.")
        except Exception:
            logger.exception("could not start a session")
            return error(503, "agent_unavailable", "The agent could not be started.")
        return web.json_response(with_connection(session, device), status=202)

    @require("app")
    async def get_session(request: web.Request) -> web.Response:
        device = request[DEVICE_KEY]
        try:
            session = manager.get(device.id, request.match_info["session_id"])
        except NotFoundError:
            return error(404, "not_found", "Unknown session.")
        return web.json_response(with_connection(session, device))

    @require("app")
    async def heartbeat(request: web.Request) -> web.Response:
        device = request[DEVICE_KEY]
        try:
            session = manager.heartbeat(device.id, request.match_info["session_id"])
        except NotFoundError:
            return error(404, "not_found", "Unknown session.")
        return web.json_response(session_view(session))

    @require("app")
    async def end_session(request: web.Request) -> web.Response:
        device = request[DEVICE_KEY]
        try:
            await manager.end(
                device.id, request.match_info["session_id"], "client_ended"
            )
        except NotFoundError:
            return error(404, "not_found", "Unknown session.")
        return web.Response(status=204)

    @require("app")
    async def status(request: web.Request) -> web.Response:
        desktop = hub.status()
        return web.json_response(
            {
                "version": version,
                "agent": await unit_state(),
                "maintenance": maintenance(),
                "desktop": {"online": desktop["online"], "device": desktop["device"]},
            }
        )

    @require("app")
    async def usage(request: web.Request) -> web.Response:
        """Claude Code, Codex and Antigravity limits, read on the PC."""
        try:
            result = await hub.call("coding.usage", {}, 20.0)
        except DesktopOfflineError:
            return error(503, "pc_offline", "The computer is not connected.")
        except DesktopTimeoutError:
            return error(504, "timeout", "The computer did not answer in time.")
        if not result.get("ok"):
            return error(
                502, "action_failed", str(result.get("error") or "Usage failed.")
            )
        return web.json_response(result.get("result") or {})

    @require("desktop")
    async def desktop_ws(request: web.Request) -> web.StreamResponse:
        return await hub.serve(request, request[DEVICE_KEY])

    @require("work")
    async def list_routines(request: web.Request) -> web.Response:
        return web.json_response({"routines": store.routines(), "timezone": "GMT-3"})

    @require("work")
    async def create_routine(request: web.Request) -> web.Response:
        try:
            routine = validate_routine(await _optional_json(request))
        except RoutineError as exc:
            return error(400, "bad_request", str(exc))
        return web.json_response(store.save_routine(routine, time.time()), status=201)

    @require("work")
    async def update_routine(request: web.Request) -> web.Response:
        routine_id = request.match_info["routine_id"]
        if store.routine(routine_id) is None:
            return error(404, "not_found", "Unknown routine.")
        try:
            routine = validate_routine(await _optional_json(request), routine_id)
        except RoutineError as exc:
            return error(400, "bad_request", str(exc))
        return web.json_response(store.save_routine(routine, time.time()))

    @require("work")
    async def delete_routine(request: web.Request) -> web.Response:
        if not store.delete_routine(request.match_info["routine_id"]):
            return error(404, "not_found", "Unknown routine.")
        return web.Response(status=204)

    @require("app")
    async def list_notifications(request: web.Request) -> web.Response:
        try:
            after = int(request.query.get("after", "0"))
        except ValueError:
            return error(400, "bad_request", "after must be a number.")
        return web.json_response({"notifications": store.notifications_after(after)})

    # The master phone: its profile, agent events, reports and commands

    @require("work")
    async def device_me(request: web.Request) -> web.Response:
        device = request[DEVICE_KEY]
        return web.json_response(
            {
                "device_id": device.id,
                "name": device.name,
                **store.profile(device.id).view(),
            }
        )

    def _cursor(text: str | None) -> int | None:
        if text in (None, "", "latest"):
            return None
        if not re.fullmatch(r"\d{1,18}", text):
            raise ValueError
        return int(text)

    @require("work", work=True)
    async def list_events(request: web.Request) -> web.Response:
        try:
            after = _cursor(request.query.get("after"))
        except ValueError:
            return error(400, "bad_request", "after must be a cursor from this API.")
        if after is None:
            return web.json_response(
                {"events": [], "cursor": str(store.latest_event_seq())}
            )
        events = store.events_after(after, limit=50)
        cursor = events[-1]["cursor"] if events else str(after)
        return web.json_response({"events": events, "cursor": cursor})

    @require("app", work=True)
    async def event_stream(request: web.Request) -> web.StreamResponse:
        device = request[DEVICE_KEY]
        try:
            after = _cursor(request.query.get("after"))
        except ValueError:
            return error(400, "bad_request", "after must be a cursor from this API.")
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)
        # Subscribe before reading the backlog so nothing falls between the two.
        queue = hub.bus.subscribe()
        last = after if after is not None else store.latest_event_seq()
        try:
            while True:
                backlog = store.events_after(last, limit=100)
                for event in backlog:
                    await ws.send_json({"type": "event", "event": event})
                    last = int(event["cursor"])
                if len(backlog) < 100:
                    break
            await ws.send_json({"type": "ready", "cursor": str(last)})

            async def pushes() -> None:
                nonlocal last
                while True:
                    try:
                        event = await asyncio.wait_for(
                            queue.get(), STREAM_RECHECK_SECONDS
                        )
                    except asyncio.TimeoutError:
                        event = None
                    if not store.device_active(device.id) or not store.can_work(
                        device.id
                    ):
                        await ws.close(
                            code=4001, message=b"device no longer authorised"
                        )
                        return
                    if event is not None and int(event["cursor"]) > last:
                        await ws.send_json({"type": "event", "event": event})
                        last = int(event["cursor"])

            sender = asyncio.ensure_future(pushes())
            try:
                async for message in ws:
                    if message.type != WSMsgType.TEXT:
                        continue
                    try:
                        data = message.json()
                    except ValueError:
                        continue
                    if (
                        data.get("type") == "ack"
                        and data.get("stage") in DELIVERY_STAGES
                    ):
                        store.mark_delivery(
                            str(data.get("event_id", ""))[:80],
                            device.id,
                            data["stage"],
                            time.time(),
                        )
            finally:
                sender.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await sender
        finally:
            hub.bus.unsubscribe(queue)
        return ws

    @require("app", work=True)
    async def ack_event(request: web.Request) -> web.Response:
        try:
            stage = str((await _optional_json(request)).get("stage", "received"))
        except RoutineError:
            return error(400, "bad_request", "Send a JSON body with a stage.")
        if stage not in DELIVERY_STAGES:
            return error(400, "bad_request", f"stage must be one of {DELIVERY_STAGES}.")
        device = request[DEVICE_KEY]
        if not store.mark_delivery(
            request.match_info["event_id"], device.id, stage, time.time()
        ):
            return error(404, "not_found", "Unknown event.")
        return web.Response(status=204)

    @require("app", work=True)
    async def get_report(request: web.Request) -> web.Response:
        event = store.event(request.match_info["event_id"])
        if event is None:
            return error(404, "not_found", "Unknown report.")
        return web.json_response(event)

    @require("app", master=True)
    async def mobile_notifications(request: web.Request) -> web.Response:
        try:
            body = await _optional_json(request)
        except RoutineError:
            return error(400, "bad_request", "Send a JSON body with items.")
        raw = body.get("items")
        if not isinstance(raw, list) or len(raw) > 50:
            return error(400, "bad_request", "items must be a list of at most 50.")
        items = []
        for item in raw:
            if not isinstance(item, dict) or item.get("app") not in SOCIAL_APPS:
                return error(
                    400, "bad_request", "Only WhatsApp and Instagram are accepted."
                )
            key = str(item.get("key") or "")[:120]
            if not key:
                return error(400, "bad_request", "Each item needs a key.")
            try:
                posted = float(item["posted_at"]) if item.get("posted_at") else None
            except (TypeError, ValueError):
                posted = None
            # Metadata only: the message text stays on the phone.
            items.append(
                {
                    "key": key,
                    "app": item["app"],
                    "sender": str(item["sender"])[:80] if item.get("sender") else None,
                    "conversation": str(item["conversation"])[:80]
                    if item.get("conversation")
                    else None,
                    "posted_at": posted,
                }
            )
        stored = store.add_mobile_notifications(
            request[DEVICE_KEY].id, items, time.time()
        )
        return web.json_response({"stored": stored})

    @require("app")
    async def run_command(request: web.Request) -> web.Response:
        try:
            body = await _optional_json(request)
        except RoutineError:
            return error(400, "bad_request", "Send the command as JSON.")
        outcome = await commands.run(request[DEVICE_KEY].id, body)
        return web.json_response(outcome.body, status=outcome.status)

    @require("app", work=True)
    async def diagnostics(request: web.Request) -> web.Response:
        device = request[DEVICE_KEY]
        return web.json_response(
            {
                "version": version,
                "agent": await unit_state(),
                "desktop": hub.status(),
                "coverage": store.coverage(),
                "event_streams": hub.bus.listeners,
                "profile": store.profile(device.id).view(),
            }
        )

    # "What are you doing?" and "stop": never behind the music queue or the PC.

    @require("app")
    async def runtime(request: web.Request) -> web.Response:
        device = request[DEVICE_KEY]
        live = [s for s in store.live_sessions() if s.device_id == device.id]
        desktop = hub.status()
        return web.json_response(
            {
                "operations": operations.runtime(device.id),
                "call": session_view(live[0]) if live else None,
                "agent": await unit_state(),
                "desktop": {"online": desktop["online"], "device": desktop["device"]},
                "checked_at": time.time(),
            }
        )

    @require("app")
    async def cancel_operation(request: web.Request) -> web.Response:
        op = await operations.cancel(
            request[DEVICE_KEY].id, request.match_info["op_id"]
        )
        if op is None:
            return error(404, "not_found", "Unknown operation.")
        return web.json_response(
            {"id": op["id"], "state": op["state"], "stage": op["stage"]}
        )

    @require("app")
    async def cancel_all(request: web.Request) -> web.Response:
        ops = await operations.cancel_all(request[DEVICE_KEY].id)
        return web.json_response(
            {"operations": [{"id": o["id"], "state": o["state"]} for o in ops]}
        )

    # Reports about JARVIS itself

    @require("app")
    async def create_report(request: web.Request) -> web.Response:
        if reports_service is None:
            return error(503, "unavailable", "Diagnostics are not configured.")
        try:
            body = await _optional_json(request)
        except RoutineError:
            return error(400, "bad_request", "Send the request as JSON.")
        report = reports_service.start(request[DEVICE_KEY].id, body)
        return web.json_response(report, status=202)

    @require("app")
    async def list_reports(request: web.Request) -> web.Response:
        return web.json_response({"reports": store.reports(30)})

    @require("app")
    async def get_report_status(request: web.Request) -> web.Response:
        report = store.report(request.match_info["report_id"])
        if report is None:
            return error(404, "not_found", "Unknown report.")
        return web.json_response(report)

    @require("app")
    async def report_file(request: web.Request) -> web.StreamResponse:
        suffix = "." + request.match_info["kind"]
        path = (
            reports_service.file(request.match_info["report_id"], suffix)
            if reports_service
            else None
        )
        if path is None:
            return error(404, "not_found", "That file is not available on the server.")
        return web.FileResponse(
            path, headers={"Content-Disposition": f'attachment; filename="{path.name}"'}
        )

    # Projects (DiceVTT): conversation with the coordinator, plans, approval, runs.

    def orchestration(handler: Handler) -> Handler:
        @require("work", work=True)
        async def wrapped(request: web.Request) -> web.StreamResponse:
            if orchestrator is None:
                return error(503, "unavailable", "Projects are not configured.")
            try:
                return await handler(request)
            except OrchestratorError as exc:
                return error(exc.status, exc.code, str(exc))

        return wrapped

    async def _body(request: web.Request) -> dict[str, Any]:
        try:
            return await _optional_json(request)
        except RoutineError:
            raise OrchestratorError(400, "bad_request", "Send JSON.") from None

    def _routing(body: dict[str, Any]) -> dict[str, Any]:
        # Passed as sent: the orchestrator validates it (never dropped here).
        return {
            k: body.get(k)
            for k in ("routing_version", "planning_agent", "execution_agent", "pipeline")
        }

    @orchestration
    async def list_projects(request: web.Request) -> web.Response:
        assert orchestrator is not None
        return web.json_response({"projects": orchestrator.projects()})

    @orchestration
    async def local_runtime(request: web.Request) -> web.Response:
        assert orchestrator is not None
        return web.json_response(await orchestrator.runtime_status())

    @orchestration
    async def list_conversations(request: web.Request) -> web.Response:
        assert orchestrator is not None
        return web.json_response(
            {"conversations": orchestrator.conversations(request.query.get("project"))}
        )

    @orchestration
    async def new_conversation(request: web.Request) -> web.Response:
        assert orchestrator is not None
        body = await _body(request)
        conv = await orchestrator.post_message(
            request[DEVICE_KEY].id,
            str(body.get("project") or "dicevtt"),
            str(body.get("text") or ""),
            request_id=str(body.get("request_id") or "")[:80] or None,
            routing=_routing(body),
        )
        return web.json_response(conv, status=202)

    @orchestration
    async def get_conversation(request: web.Request) -> web.Response:
        assert orchestrator is not None
        return web.json_response(orchestrator.conversation(request.match_info["cid"]))

    @orchestration
    async def new_message(request: web.Request) -> web.Response:
        assert orchestrator is not None
        body = await _body(request)
        conv = orchestrator.conversation(request.match_info["cid"])
        conv = await orchestrator.post_message(
            request[DEVICE_KEY].id,
            conv["project"],
            str(body.get("text") or ""),
            conversation_id=conv["id"],
            request_id=str(body.get("request_id") or "")[:80] or None,
            routing=_routing(body),
        )
        return web.json_response(conv, status=202)

    @orchestration
    async def pending_plans(request: web.Request) -> web.Response:
        assert orchestrator is not None
        return web.json_response({"plans": orchestrator.pending_plans()})

    @orchestration
    async def decide_plan(request: web.Request) -> web.Response:
        assert orchestrator is not None
        body = await _body(request)
        version = body.get("version")
        result = await orchestrator.decide(
            request[DEVICE_KEY].id,
            request.match_info["plan_id"],
            request.match_info["decision"],
            version=int(version) if version is not None else None,
            plan_hash_value=str(body["hash"]) if body.get("hash") else None,
            text=str(body.get("text") or "")[:1000] or None,
        )
        return web.json_response(result)

    @orchestration
    async def get_run(request: web.Request) -> web.Response:
        assert orchestrator is not None
        return web.json_response(orchestrator.run(request.match_info["run_id"]))

    @orchestration
    async def cancel_run(request: web.Request) -> web.Response:
        assert orchestrator is not None
        return web.json_response(
            await orchestrator.cancel_run(request.match_info["run_id"])
        )

    @orchestration
    async def apply_run(request: web.Request) -> web.Response:
        assert orchestrator is not None
        return web.json_response(
            await orchestrator.apply(
                request.match_info["run_id"], request[DEVICE_KEY].id
            )
        )

    @orchestration
    async def orchestration_active(request: web.Request) -> web.Response:
        assert orchestrator is not None
        return web.json_response({"active": orchestrator.active()})

    @orchestration
    async def orchestration_cancel(request: web.Request) -> web.Response:
        assert orchestrator is not None
        body = await _body(request)
        agent = body.get("agent")
        if agent:
            return web.json_response(
                {"stopped": await orchestrator.cancel_agent(str(agent))}
            )
        return web.json_response({"runs": await orchestrator.cancel_all()})

    # DiceVTT RAG: runs on the primary PC with the helper; the phones reach it here.

    async def rag_call(
        action: str, params: dict[str, Any], timeout: float
    ) -> web.Response:
        try:
            result = await hub.call(action, params, timeout)
        except DesktopOfflineError:
            return error(
                503, "pc_offline", "O PC principal (helper + RAG) não está conectado."
            )
        except DesktopTimeoutError:
            return error(504, "timeout", "O PC principal não respondeu a tempo.")
        if not result.get("ok"):
            return error(
                502, "rag_failed", str(result.get("error") or "O RAG falhou no PC.")
            )
        return web.json_response(result.get("result") or {})

    async def rag_body(request: web.Request) -> dict[str, Any]:
        def bad(message: str) -> web.HTTPBadRequest:
            return web.HTTPBadRequest(
                text=json.dumps({"error": "bad_request", "message": message}),
                content_type="application/json",
            )

        try:
            body = await _optional_json(request)
        except RoutineError:
            raise bad("Send JSON.") from None
        if str(body.get("project_id") or "dicevtt") != "dicevtt":
            raise bad("Only the dicevtt project has a RAG.")
        return body

    def rag_text(body: dict[str, Any]) -> str | None:
        text = str(body.get("query") or "").strip()
        return text[:2000] if text else None

    @require("work", work=True)
    async def rag_health(request: web.Request) -> web.Response:
        return await rag_call("rag.health", {}, 10)

    @require("work", work=True)
    async def rag_retrieve(request: web.Request) -> web.Response:
        body = await rag_body(request)
        query = rag_text(body)
        if query is None:
            return error(400, "bad_request", "Envie a pergunta em query.")
        return await rag_call(
            "rag.retrieve",
            {"query": query, "text_limit": body.get("text_limit") or 6000},
            60,
        )

    @require("work", work=True)
    async def rag_ask(request: web.Request) -> web.Response:
        body = await rag_body(request)
        query = rag_text(body)
        if query is None:
            return error(400, "bad_request", "Envie a pergunta em query.")
        request_id = str(body.get("request_id") or "")[:80] or None
        response = await rag_call(
            "rag.ask", {"query": query, "request_id": request_id}, 30
        )
        if response.status == 200:
            response.set_status(202)
        return response

    @require("work", work=True)
    async def rag_ask_status(request: web.Request) -> web.Response:
        return await rag_call(
            "rag.ask_status", {"ask_id": request.match_info["ask_id"]}, 15
        )

    @require("work", work=True)
    async def rag_ask_cancel(request: web.Request) -> web.Response:
        return await rag_call(
            "rag.ask_cancel", {"ask_id": request.match_info["ask_id"]}, 15
        )

    @require("work", work=True)
    async def rag_index(request: web.Request) -> web.Response:
        body = await rag_body(request)
        response = await rag_call(
            "rag.index", {"scope": str(body.get("scope") or "all")}, 30
        )
        if response.status == 200:
            response.set_status(202)
        return response

    @require("work", work=True)
    async def rag_index_status(request: web.Request) -> web.Response:
        return await rag_call(
            "rag.index_status", {"job_id": request.match_info["job_id"]}, 15
        )

    # The phone's diagnostics carry its own log: larger bodies than other calls.
    browser_middleware, browser_routes = browser_surface(store, limiter)
    app = web.Application(
        middlewares=[limit_requests, browser_middleware],
        client_max_size=4 * 1024 * 1024,
    )
    app.add_routes(
        [
            web.get("/v1/health", health),
            web.get("/v1/integrations", personal_connections),
            web.patch("/v1/integrations/{account_id}", update_personal_connection),
            web.post("/v1/pair", pair),
            web.post("/v1/sessions", create_session),
            web.get("/v1/sessions/{session_id}", get_session),
            web.post("/v1/sessions/{session_id}/heartbeat", heartbeat),
            web.delete("/v1/sessions/{session_id}", end_session),
            web.get("/v1/status", status),
            web.get("/v1/desktop/ws", desktop_ws),
            web.get("/v1/routines", list_routines),
            web.post("/v1/routines", create_routine),
            web.put("/v1/routines/{routine_id}", update_routine),
            web.delete("/v1/routines/{routine_id}", delete_routine),
            web.get("/v1/notifications", list_notifications),
            web.get("/v1/devices/me", device_me),
            web.get("/v1/events", list_events),
            web.get("/v1/events/stream", event_stream),
            web.post("/v1/events/{event_id}/ack", ack_event),
            web.get("/v1/reports/{event_id}", get_report),
            web.post("/v1/mobile-notifications", mobile_notifications),
            web.post("/v1/commands", run_command),
            web.get("/v1/diagnostics", diagnostics),
            web.get("/v1/usage", usage),
            web.get("/v1/runtime", runtime),
            web.post("/v1/operations/cancel-all", cancel_all),
            web.post("/v1/operations/{op_id}/cancel", cancel_operation),
            web.post("/v1/diagnostic-reports", create_report),
            web.get("/v1/diagnostic-reports", list_reports),
            web.get("/v1/diagnostic-reports/{report_id}", get_report_status),
            web.get("/v1/diagnostic-reports/{report_id}/{kind:md|zip}", report_file),
            web.get("/v1/projects", list_projects),
            web.get("/v1/orchestration/runtime", local_runtime),
            web.get("/v1/conversations", list_conversations),
            web.post("/v1/conversations", new_conversation),
            web.get("/v1/conversations/{cid}", get_conversation),
            web.post("/v1/conversations/{cid}/messages", new_message),
            web.get("/v1/plans/pending", pending_plans),
            web.post("/v1/plans/{plan_id}/{decision:approve|reject}", decide_plan),
            web.get("/v1/runs/{run_id}", get_run),
            web.post("/v1/runs/{run_id}/cancel", cancel_run),
            web.post("/v1/runs/{run_id}/apply", apply_run),
            web.get("/v1/orchestration/active", orchestration_active),
            web.post("/v1/orchestration/cancel", orchestration_cancel),
            web.get("/v1/rag/health", rag_health),
            web.post("/v1/rag/retrieve", rag_retrieve),
            web.post("/v1/rag/asks", rag_ask),
            web.get("/v1/rag/asks/{ask_id:[A-Za-z0-9]{1,64}}", rag_ask_status),
            web.post("/v1/rag/asks/{ask_id:[A-Za-z0-9]{1,64}}/cancel", rag_ask_cancel),
            web.post("/v1/rag/index-jobs", rag_index),
            web.get("/v1/rag/index-jobs/{job_id:[A-Za-z0-9]{1,64}}", rag_index_status),
            *catalog_routes(Catalog(store), require, DEVICE_KEY),
            *browser_routes,
            *release_routes(require),
            *(extra_routes or []),
        ]
    )
    return app


def apply_music_policy(
    action: str, params: dict[str, Any], forced_target: str | None
) -> dict[str, Any]:
    """The agent's Spotify actions during a master-phone session: the computer only."""
    if forced_target is None or not action.startswith("spotify."):
        return params
    requested = params.get("device")
    if requested not in (None, "", forced_target):
        raise PermissionError("Music from the master phone plays only on the computer.")
    return {**params, "device": forced_target}


def build_internal_app(
    *,
    hub: DesktopHub,
    token: str,
    music_target: Callable[[], str | None] = lambda: None,
    store: Store | None = None,
    orchestrator: Orchestrator | None = None,
    personal: PersonalGateway | None = None,
) -> web.Application:
    @web.middleware
    async def check_token(request: web.Request, handler: Handler) -> web.StreamResponse:
        if not hmac.compare_digest(_bearer(request).encode(), token.encode()):
            return error(401, "unauthorized", "Missing or wrong internal token.")
        return await handler(request)

    async def desktop_status(request: web.Request) -> web.Response:
        return web.json_response(hub.status())

    async def desktop_action(request: web.Request) -> web.Response:
        try:
            body = await request.json()
            action = str(body["action"])
            params = dict(body.get("params") or {})
            timeout = min(max(float(body.get("timeout", 25)), 1.0), 120.0)
        except (ValueError, KeyError, TypeError):
            return error(400, "bad_request", "Send action, params and timeout.")
        if action == "orchestrator.progress" and orchestrator is not None:
            return web.json_response({"ok": True, "result": orchestrator.progress()})
        try:
            params = apply_music_policy(action, params, music_target())
        except PermissionError as exc:
            return error(403, "policy", str(exc))
        try:
            result = await hub.call(action, params, timeout)
        except DesktopOfflineError:
            return error(503, "pc_offline", "The computer is not connected.")
        except DesktopTimeoutError:
            return error(504, "timeout", "The computer did not answer in time.")
        if result.get("ok"):
            return web.json_response({"ok": True, "result": result.get("result") or {}})
        return web.json_response(
            {
                "ok": False,
                "error": "action_failed",
                "message": str(result.get("error") or "The action failed."),
            }
        )

    async def conversation(request: web.Request) -> web.Response:
        """The voice agent's conversation, as it happens (kept for reports)."""
        if store is None:
            return web.json_response({"stored": 0})
        try:
            body = await request.json()
            items = [
                {
                    "room": str(i["room"])[:80],
                    "kind": str(i.get("kind", "message"))[:20],
                    "role": str(i["role"])[:20] if i.get("role") else None,
                    "text": str(i["text"])[:8000] if i.get("text") else None,
                    "data": i.get("data") if isinstance(i.get("data"), dict) else None,
                    "at": float(i["at"]),
                }
                for i in body["items"][:500]
            ]
        except (ValueError, KeyError, TypeError):
            return error(400, "bad_request", "Send items with room, kind and at.")
        return web.json_response({"stored": store.add_conversation_items(items)})

    async def personal_availability(request: web.Request) -> web.Response:
        """Which personal accounts this room's session may use (none when denied)."""
        if personal is None:
            return web.json_response({"available": False, "accounts": []})
        return web.json_response(personal.availability(request.query.get("room", "")))

    async def personal_tool(request: web.Request) -> web.Response:
        if personal is None:
            return error(403, "runtime_disabled", "Personal data is not enabled.")
        try:
            body = await request.json()
            call = Call(
                request.match_info["tool"],
                body.get("arguments") or {},
                str(body.get("room") or ""),
            )
        except (ValueError, TypeError, AttributeError):
            return error(400, "bad_request", "Send room and arguments.")
        try:
            return web.json_response(await personal.run(call))
        except PersonalDeniedError as exc:
            return error(403, exc.code, str(exc))
        except InvalidArgumentsError as exc:
            return error(400, "invalid_arguments", str(exc))

    app = web.Application(middlewares=[check_token], client_max_size=4 * 1024 * 1024)
    app.add_routes(
        [
            web.get("/internal/v1/desktop", desktop_status),
            web.post("/internal/v1/desktop/actions", desktop_action),
            web.post("/internal/v1/conversation", conversation),
            web.get("/internal/v1/personal", personal_availability),
            web.post("/internal/v1/personal/{tool}", personal_tool),
        ]
    )
    return app
