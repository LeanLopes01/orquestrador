"""Serviço RAG duradouro (127.0.0.1:8767): um processo, um worker, sem autoreload.

Health não carrega modelo e distingue processo online, índice pronto e geração pronta.
Jobs e asks ficam no SQLite; reinício marca os em execução como interrupted.
"""

from __future__ import annotations

import contextlib
import hmac
import logging
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from . import __version__
from .config import RagConfig
from .orchestrator import CapabilityUnavailable, RagOrchestrator

logger = logging.getLogger("unity_rag")
MAX_TEXT_LIMIT = 60_000


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


def create_app(config: RagConfig, *, orchestrator: RagOrchestrator | None = None, on_shutdown=None):

    from .airllm_engine import GenerationCancelled
    from .retrieval import QueryError

    token = ensure_token(config.token_path)
    rag = orchestrator or RagOrchestrator(config)
    allowed_hosts = {f"127.0.0.1:{config.port}", f"localhost:{config.port}"}
    started_at = time.time()
    cancels: dict[str, threading.Event] = {}
    startup_error: list[str] = []

    def boot() -> None:
        try:
            rag.start()
        except Exception as exc:  # o processo segue respondendo health com o motivo
            logger.exception("falha ao iniciar o RAG")
            startup_error.append(f"{type(exc).__name__}: {exc}")
            rag.started.set()

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        thread = threading.Thread(target=boot, name="rag-boot", daemon=True)
        thread.start()
        try:
            yield
        finally:
            for event in cancels.values():
                event.set()
            await _to_thread(rag.close)

    async def _to_thread(fn, *args):
        import asyncio

        return await asyncio.to_thread(fn, *args)

    app = FastAPI(title="unity-rag", version=__version__, docs_url=None, redoc_url=None, openapi_url=None,
                  lifespan=lifespan)

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        client = request.client.host if request.client else ""
        if client not in {"127.0.0.1", "::1"} or request.headers.get("host") not in allowed_hosts:
            return JSONResponse({"error": "forbidden", "message": "Somente acesso local."}, status_code=403)
        if request.headers.get("origin"):
            return JSONResponse({"error": "forbidden", "message": "Use a ponte local."}, status_code=403)
        if not hmac.compare_digest(request.headers.get("x-local-token", ""), token):
            return JSONResponse({"error": "unauthorized", "message": "Token local ausente ou inválido."}, status_code=401)
        return await call_next(request)

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, dict) else {"error": "request_failed", "message": str(exc.detail)}
        return JSONResponse(detail, status_code=exc.status_code)

    @app.exception_handler(CapabilityUnavailable)
    async def unavailable(_request: Request, exc: CapabilityUnavailable) -> JSONResponse:
        return JSONResponse({"error": exc.code, "message": str(exc)}, status_code=503)

    async def body_of(request: Request) -> dict[str, Any]:
        try:
            body = await request.json()
        except ValueError:
            raise HTTPException(400, "Envie JSON.") from None
        if not isinstance(body, dict):
            raise HTTPException(400, "Envie um objeto JSON.")
        if str(body.get("project_id") or config.project_id) != config.project_id:
            raise HTTPException(400, f"Este serviço atende somente o projeto {config.project_id}.")
        return body

    @app.get("/v1/rag/health")
    async def health() -> dict[str, Any]:
        details = await _to_thread(rag.health) if rag.started.is_set() else {}
        return {
            "service": "unity-rag", "online": True, "version": __version__, "project_id": config.project_id,
            "pid": os.getpid(), "started_at": started_at, "starting": not rag.started.is_set(),
            "startup_error": startup_error[0] if startup_error else None, **details,
        }

    @app.post("/v1/rag/retrieve")
    async def retrieve(request: Request) -> dict[str, Any]:
        body = await body_of(request)
        limit = min(max(int(body.get("text_limit") or 20_000), 200), MAX_TEXT_LIMIT)
        try:
            result = await _to_thread(rag.retrieve, str(body.get("query") or ""))
        except QueryError as exc:
            raise HTTPException(400, str(exc)) from None
        return result.to_dict(text_limit=limit)

    @app.get("/v1/rag/document-folder")
    async def document_folder() -> dict[str, Any]:
        from .document_extract import SUPPORTED
        return {"path": str(config.docs_root), "exists": config.docs_root.is_dir(),
                "formats": sorted(SUPPORTED), "max_file_mb": 32, "mode": "manual"}

    @app.post("/v1/rag/document-folder/open")
    async def open_document_folder(request: Request) -> dict[str, Any]:
        await body_of(request)
        if os.name != 'nt':
            raise HTTPException(400, 'Abertura da pasta disponível somente no Windows.')
        config.docs_root.mkdir(parents=True, exist_ok=True)
        os.startfile(str(config.docs_root))
        return {"opened": True, "path": str(config.docs_root)}

    @app.post("/v1/rag/index-jobs", status_code=202)
    async def index_job(request: Request) -> dict[str, Any]:
        body = await body_of(request)
        scope = str(body.get("scope") or "all")
        if scope not in {"code", "documents", "all"}:
            raise HTTPException(400, "scope deve ser code, documents ou all.")
        rag._require_index()
        job_id = rag.state.create_job(scope)
        future = rag.submit_index(scope)
        rag.state.update_job(job_id, state="running")

        def done(fut) -> None:
            try:
                rag.state.update_job(job_id, state="completed", report=fut.result())
            except Exception as exc:
                rag.state.update_job(job_id, state="failed", error=f"{type(exc).__name__}: {exc}")

        future.add_done_callback(done)
        return {"job_id": job_id, "state": "running", "scope": scope}

    @app.get("/v1/rag/index-jobs/{job_id}")
    async def get_job(job_id: str) -> dict[str, Any]:
        rag._require_index()
        job = rag.state.job(job_id)
        if job is None:
            raise HTTPException(404, "Job desconhecido ou expirado.")
        return job

    @app.post("/v1/rag/asks", status_code=202)
    async def create_ask(request: Request) -> dict[str, Any]:
        body = await body_of(request)
        query = str(body.get("query") or "").strip()
        if not query:
            raise HTTPException(400, "A pergunta está vazia.")
        if len(query) > config.retrieval.max_query_chars:
            raise HTTPException(400, f"A pergunta excede {config.retrieval.max_query_chars} caracteres.")
        rag._require_index()
        model = rag.health()["model"]
        if model["state"] in {"not_configured", "error"} and model["reason"]:
            raise CapabilityUnavailable("generator_unavailable", f"Geração indisponível: {model['reason']}")
        request_id = str(body.get("request_id") or "")[:80] or None
        rag.state.expire(config.result_ttl_hours * 3600)
        existing = rag.state.ask_by_request(request_id) if request_id else None
        if existing is not None:  # reenvio/polling: nunca duplica a geração
            return {"ask_id": existing["id"], **existing}
        active = [a for a in rag.state.recent_asks(50) if a["state"] in {"queued", "running"}]
        if len(active) >= config.ask_queue_limit:
            raise HTTPException(429, f"Fila de geração cheia ({config.ask_queue_limit}). Aguarde.")
        ask_id, created = rag.state.create_ask(request_id, query)
        if not created:
            return {"ask_id": ask_id, **(rag.state.ask(ask_id) or {})}
        cancel = threading.Event()
        cancels[ask_id] = cancel

        def progress(event) -> None:
            rag.state.update_ask(ask_id, state="running", progress=event.to_dict())

        future = rag.ask_async(query, progress, cancel=cancel, request_id=ask_id)

        def done(fut) -> None:
            cancels.pop(ask_id, None)
            try:
                rag.state.update_ask(ask_id, state="completed", result=fut.result().to_dict())
            except GenerationCancelled:
                rag.state.update_ask(ask_id, state="cancelled", error="Cancelado a pedido.")
            except CapabilityUnavailable as exc:
                rag.state.update_ask(ask_id, state="failed", error=f"{exc.code}: {exc}")
            except Exception as exc:
                logger.exception("ask %s falhou", ask_id)
                rag.state.update_ask(ask_id, state="failed", error=f"{type(exc).__name__}: {exc}")

        future.add_done_callback(done)
        return {"ask_id": ask_id, "state": "queued", "query": query}

    @app.get("/v1/rag/asks")
    async def list_asks() -> dict[str, Any]:
        rag._require_index()
        return {"asks": rag.state.recent_asks(20)}

    @app.get("/v1/rag/asks/{ask_id}")
    async def get_ask(ask_id: str) -> dict[str, Any]:
        rag._require_index()
        ask = rag.state.ask(ask_id)
        if ask is None:
            raise HTTPException(404, "Pedido desconhecido ou expirado.")
        return ask

    @app.post("/v1/rag/asks/{ask_id}/cancel")
    async def cancel_ask(ask_id: str) -> dict[str, Any]:
        event = cancels.get(ask_id)
        if event is None:
            return {"cancelled": False, "message": "Pedido não está em execução."}
        event.set()  # o worker para no próximo token; nenhuma geração paralela começa antes
        return {"cancelled": True}

    @app.post("/v1/rag/shutdown")
    async def shutdown() -> dict[str, Any]:
        if on_shutdown is not None:
            threading.Timer(0.2, on_shutdown).start()
        return {"stopping": True}

    return app
