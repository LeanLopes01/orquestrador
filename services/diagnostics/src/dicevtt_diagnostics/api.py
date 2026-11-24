"""API local do runner (127.0.0.1:8768). Mesmas regras das outras pontes: só loopback, Host
conferido, sem Origin de navegador e com X-Local-Token. Operações fixas; nenhum caminho vem do cliente.
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from . import __version__
from .config import DiagnosticsConfig
from .investigate import Investigator
from .jobs import Runner, SubmitError
from .settings import RevisionConflict, SettingsError, SettingsStore
from .store import AuditStore

logger = logging.getLogger("dicevtt_diagnostics")
RUN_ID = re.compile(r"^AUD-\d{8}-\d{6}-[0-9a-f]{6}$")
KEY = re.compile(r"^[A-Za-z0-9-]{8,80}$")
STATES = ("queued", "collecting", "completed", "partial", "failed", "cancelled", "interrupted")
SEVERITIES = ("high", "medium", "low", "info")


def sha256_of_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def ensure_token(path: Path) -> str:
    try:
        token = path.read_text(encoding="ascii").strip()
        if len(token) >= 32:
            return token
    except FileNotFoundError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(32)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(token, encoding="ascii")
    os.replace(tmp, path)
    return token


def create_app(config: DiagnosticsConfig, *, runner: Runner | None = None, on_shutdown=None) -> FastAPI:
    token = ensure_token(config.token_path)
    store = runner.store if runner else AuditStore(config.state_path)
    settings = runner.settings if runner else SettingsStore(config.settings_path)
    runner = runner or Runner(config, store, settings)
    investigator = Investigator(config, store, settings)
    runner.on_finished = investigator.after_audit
    allowed_hosts = {f"127.0.0.1:{config.port}", f"localhost:{config.port}"}
    started_at = time.time()

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        runner.start()
        investigator.start()
        try:
            yield
        finally:
            runner.stop()
            investigator.stop()
            store.close()

    app = FastAPI(title="dicevtt-diagnostics", version=__version__, docs_url=None, redoc_url=None,
                  openapi_url=None, lifespan=lifespan)

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        client = request.client.host if request.client else ""
        if client not in {"127.0.0.1", "::1"} or request.headers.get("host") not in allowed_hosts:
            return JSONResponse({"error": "forbidden", "message": "Somente acesso local."}, status_code=403)
        if request.headers.get("origin"):
            return JSONResponse({"error": "forbidden", "message": "Use a ponte local."}, status_code=403)
        if not hmac.compare_digest(request.headers.get("x-local-token", ""), token):
            return JSONResponse({"error": "unauthorized", "message": "Token local ausente ou inválido."},
                                status_code=401)
        return await call_next(request)

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, dict) else {"error": "request_failed", "message": str(exc.detail)}
        return JSONResponse(detail, status_code=exc.status_code)

    async def body_of(request: Request) -> dict[str, Any]:
        try:
            body = await request.json()
        except ValueError:
            raise HTTPException(400, "Envie JSON.") from None
        if not isinstance(body, dict):
            raise HTTPException(400, "Envie um objeto JSON.")
        return body

    def run_or_404(run_id: str) -> dict[str, Any]:
        run = store.run(run_id) if RUN_ID.match(run_id) else None
        if run is None:
            raise HTTPException(404, "Auditoria desconhecida.")
        return run

    @app.get("/v1/diagnostics/health")
    async def health() -> dict[str, Any]:
        try:
            current, settings_error = settings.load().to_dict(), None
        except SettingsError as exc:
            current, settings_error = None, str(exc)
        return {
            "service": "dicevtt-diagnostics", "online": True, "version": __version__, "pid": os.getpid(),
            "started_at": started_at, "project_id": config.project_id, "project": config.project_name,
            "project_root": config.project_root.as_posix(),
            "capabilities": {"profiles": ["startup-light", "full-audit"] if config.full else ["startup-light"],
                             "full_audit": config.full is not None, "sync": False,
                             "ai_investigation": True, "auto_fix": False},
            "settings": current, "settings_error": settings_error,
            "active": [{"id": r["id"], "state": r["state"], "profile": r["profile"], "trigger": r["trigger"],
                        "checks_done": r["checks_done"], "checks_total": r["checks_total"]} for r in store.active()],
            "current": runner.current, "investigating": investigator.current,
            "last_run": store.latest_finished(), "last_startup": store.last_startup(),
            "sync": {"state": "local_only", "message": "Sincronização com o servidor ainda não implementada."},
        }

    @app.get("/v1/settings")
    async def get_settings() -> dict[str, Any]:
        try:
            return settings.load().to_dict()
        except SettingsError as exc:
            raise HTTPException(409, {"error": "settings_unreadable", "message": str(exc)}) from None

    @app.put("/v1/settings")
    async def put_settings(request: Request) -> dict[str, Any]:
        body = await body_of(request)
        if not isinstance(body.get("settings"), dict) or not isinstance(body.get("expected_revision"), int):
            raise HTTPException(400, "Envie {settings, expected_revision}.")
        try:
            return settings.save(body["settings"], body["expected_revision"]).to_dict()
        except SettingsError as exc:
            raise HTTPException(400, {"error": "invalid_settings", "message": str(exc)}) from None
        except RevisionConflict as exc:
            raise HTTPException(409, {"error": "revision_conflict", "message": str(exc),
                                      "current": exc.current.to_dict()}) from None

    @app.post("/v1/audits")
    async def create_audit(request: Request) -> JSONResponse:
        key = request.headers.get("idempotency-key", "")
        if not KEY.match(key):
            raise HTTPException(400, "Idempotency-Key obrigatório (8 a 80 caracteres A-Z, 0-9 e -).")
        body = await body_of(request)
        if body.get("project") not in (None, config.project_name, config.project_id):
            raise HTTPException(400, f"Este runner atende somente {config.project_name}.")
        if body.get("auto_fix") not in (None, False):
            raise HTTPException(400, "Correção automática não é suportada.")
        if body.get("startup_id") not in (None, key):
            raise HTTPException(400, "startup_id deve ser igual ao Idempotency-Key.")
        profile = body.get("profile")
        if profile is not None and not isinstance(profile, str):
            raise HTTPException(400, "profile inválido.")
        try:
            result = runner.submit(key, str(body.get("trigger") or "manual"), profile)
        except SubmitError as exc:
            raise HTTPException(409 if exc.code == "settings_unreadable" else 400,
                                {"error": exc.code, "message": str(exc)}) from None
        payload = {**result, "coalesced": result["outcome"] == "coalesced"}
        status = 202 if result["outcome"] == "created" and not result["duplicate"] else 200
        return JSONResponse(payload, status_code=status)

    @app.get("/v1/audits")
    async def list_audits(cursor: str | None = None, limit: int = 20, state: str | None = None,
                          severity: str | None = None) -> dict[str, Any]:
        if state is not None and state not in STATES:
            raise HTTPException(400, "Estado inválido.")
        if severity is not None and severity not in SEVERITIES:
            raise HTTPException(400, "Gravidade inválida.")
        if cursor is not None and not re.fullmatch(r"[0-9T:.+-]{10,40}\|AUD-[0-9a-f-]{20,30}", cursor):
            raise HTTPException(400, "Cursor inválido.")
        return store.runs(min(max(limit, 1), 50), cursor, state, severity)

    @app.get("/v1/audits/{run_id}")
    async def get_audit(run_id: str) -> dict[str, Any]:
        run = run_or_404(run_id)
        art = store.artifact(run_id, "json")
        if art is not None:  # detalhe completo vem do relatório gerado e conferido por hash
            path = config.runs_root / run_id / art["name"]
            if sha256_of_file(path) == art["sha256"]:
                run["report"] = json.loads(path.read_text(encoding="utf-8"))
            else:
                run["report_error"] = "Relatório no disco diferente do registrado (hash divergente)."
        investigation = store.investigation(run_id)
        if investigation is not None:  # hipóteses ficam à parte do relatório dos coletores
            path = config.runs_root / run_id / "investigation.json"
            if investigation.get("result_sha256") and sha256_of_file(path) == investigation["result_sha256"]:
                investigation["result"] = json.loads(path.read_text(encoding="utf-8"))
            elif investigation.get("result_sha256"):
                investigation["result_error"] = "Investigação no disco diferente da registrada (hash divergente)."
            run["investigation"] = investigation
        return run

    @app.post("/v1/audits/{run_id}/investigation")
    async def investigate(run_id: str) -> JSONResponse:
        run = run_or_404(run_id)
        if run["state"] not in ("completed", "partial"):
            raise HTTPException(409, "Só relatórios concluídos ou parciais podem ser investigados.")
        result = investigator.request(run_id, "manual")
        return JSONResponse(result, status_code=202 if result["created"] else 200)

    @app.get("/v1/audits/{run_id}/report")
    async def get_report(run_id: str, format: str = "json") -> Response:
        run_or_404(run_id)
        if format not in {"json", "html"}:
            raise HTTPException(400, "format deve ser json ou html.")
        art = store.artifact(run_id, format)
        if art is None:
            raise HTTPException(404, "Relatório ainda não gerado para esta auditoria.")
        path = config.runs_root / run_id / art["name"]
        if sha256_of_file(path) != art["sha256"]:
            raise HTTPException(409, "Relatório no disco diferente do registrado (hash divergente).")
        media = "application/json" if format == "json" else "text/html"
        return Response(path.read_bytes(), media_type=f"{media}; charset=utf-8", headers={
            "Content-Disposition": f'attachment; filename="{run_id}.{format}"',
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
            "X-Content-Type-Options": "nosniff",
        })

    @app.post("/v1/audits/{run_id}/cancel")
    async def cancel(run_id: str) -> dict[str, Any]:
        run_or_404(run_id)
        return runner.cancel(run_id)

    @app.post("/v1/diagnostics/shutdown")
    async def shutdown() -> dict[str, Any]:
        if on_shutdown is not None:
            threading.Timer(0.2, on_shutdown).start()
        return {"stopping": True}

    return app
