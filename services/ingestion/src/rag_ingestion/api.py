"""Serviço HTTP local da ingestão (127.0.0.1:8766). Um processo, um worker de lotes.

Somente loopback, Host conferido, sem CORS e com token local entre a ponte e o
serviço. O navegador nunca recebe o token; a ponte Vite o injeta.
"""

from __future__ import annotations

import contextlib
import hmac
import logging
import os
import secrets
import threading
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from . import __version__
from .acquisition import clean_temporaries as clean_cache_temporaries
from .config import IngestionConfig
from .events import EventLog
from .inputs import InputError, from_manifest, from_text, parse_catalog
from .pipeline import Pipeline
from .repository import Repository
from .storage import clean_temporaries

logger = logging.getLogger("rag_ingestion")
MAX_DOCUMENT_BYTES = 256 * 1024


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


class BatchWorker:
    def __init__(self, pipeline: Pipeline, repository: Repository) -> None:
        self._pipeline = pipeline
        self._repository = repository
        self._wake = threading.Event()
        self._stop = threading.Event()
        self.current: str | None = None
        self._thread = threading.Thread(target=self._loop, name="ingestion-batches", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def notify(self) -> None:
        self._wake.set()

    def stop(self) -> None:
        self._stop.set()
        self._pipeline.cancel.set()
        self._wake.set()
        self._thread.join(timeout=30)

    def _loop(self) -> None:
        while not self._stop.is_set():
            batch_id = self._repository.next_queued()
            if batch_id is None:
                self._wake.wait(5)
                self._wake.clear()
                continue
            self.current = batch_id
            try:
                self._pipeline.run_batch(batch_id)
            except Exception:
                logger.exception("lote %s falhou", batch_id)
                self._repository.set_batch_state(batch_id, "interrupted")
            finally:
                self.current = None


def create_app(config: IngestionConfig, *, pipeline: Pipeline | None = None, on_shutdown=None):

    token = ensure_token(config.token_path)
    repository = pipeline.repository if pipeline else Repository(config.state_path)
    recovered = repository.recover()
    clean_temporaries(config.output_root)
    clean_cache_temporaries(config.cache_root)
    pipeline = pipeline or Pipeline(config, repository, EventLog(config.log_path))
    worker = BatchWorker(pipeline, repository)
    allowed_hosts = {f"127.0.0.1:{config.port}", f"localhost:{config.port}"}

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        worker.start()
        logger.info("ingestão pronta em %s:%s (recuperação: %s)", config.host, config.port, recovered)
        try:
            yield
        finally:
            worker.stop()

    app = FastAPI(title="rag-ingestion", version=__version__, docs_url=None, redoc_url=None, openapi_url=None,
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

    def project(body: dict[str, Any]) -> None:
        if str(body.get("project_id") or config.project_id) != config.project_id:
            raise HTTPException(400, f"Este serviço atende somente o projeto {config.project_id}.")

    @app.get("/v1/ingestion/health")
    def health() -> dict[str, Any]:
        writable = {}
        for name, path in (("output", config.output_root), ("cache", config.cache_root)):
            try:
                path.mkdir(parents=True, exist_ok=True)
                probe = path / f".probe-{secrets.token_hex(3)}"
                probe.write_bytes(b"")
                probe.unlink()
                writable[name] = True
            except OSError:
                writable[name] = False
        deps = {}
        for module in ("trafilatura", "youtube_transcript_api"):
            try:
                __import__(module)
                deps[module] = True
            except ImportError:
                deps[module] = False
        return {"service": "rag-ingestion", "online": True, "version": __version__,
                "project_id": config.project_id, "default_mode": config.default_mode,
                "output_root": str(config.output_root), "writable": writable, "dependencies": deps,
                "catalog_available": bool(config.catalog_path and config.catalog_path.exists()),
                "running_batch": worker.current, "pid": os.getpid()}

    @app.post("/v1/ingestion/batches", status_code=202)
    async def create_batch(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except ValueError:
            raise HTTPException(400, "Envie JSON.") from None
        if not isinstance(body, dict):
            raise HTTPException(400, "Envie um objeto JSON.")
        project(body)
        mode = str(body.get("mode") or config.default_mode)
        if mode not in {"online", "offline"}:
            raise HTTPException(400, "mode deve ser online ou offline.")
        request_id = str(body.get("request_id") or "")[:80] or None
        payload = {k: body.get(k) for k in ("mode", "manifest", "urls", "catalog")}
        digest = repository.payload_hash(payload)
        if request_id:
            existing = repository.find_request(request_id)
            if existing is not None:
                if existing["payload_hash"] != digest:
                    return JSONResponse({"error": "conflict", "message": "request_id já usado com outro conteúdo."},
                                        status_code=409)
                return JSONResponse(repository.batch(existing["id"], limit=0), status_code=202)
        try:
            if body.get("catalog"):
                if not config.catalog_path:
                    raise InputError("catalog_path não configurado.")
                _, items = parse_catalog(config.catalog_path.read_text(encoding="utf-8-sig"))
                label = f"catálogo {config.catalog_path.name}"
            elif body.get("manifest") is not None:
                items, label = from_manifest(body["manifest"]), "manifesto da UI"
            elif isinstance(body.get("urls"), str):
                items, label = from_text(body["urls"]), "lista de URLs"
            else:
                raise InputError("Envie manifest, urls ou catalog=true.")
        except (InputError, OSError) as exc:
            raise HTTPException(400, str(exc)) from None
        if not items:
            raise HTTPException(400, "Nenhuma fonte para coletar.")
        batch_id = repository.create_batch(config.project_id, mode, items, request_id=request_id,
                                           payload_hash=digest, label=label)
        worker.notify()
        return JSONResponse(repository.batch(batch_id, limit=0), status_code=202)

    @app.get("/v1/ingestion/batches")
    def list_batches(limit: int = 20, offset: int = 0) -> dict[str, Any]:
        return {"batches": repository.batches(limit=max(1, min(limit, 100)), offset=max(0, offset))}

    @app.get("/v1/ingestion/batches/{batch_id}")
    def get_batch(batch_id: str, limit: int = 200, offset: int = 0) -> dict[str, Any]:
        batch = repository.batch(batch_id, limit=max(0, min(limit, 500)), offset=max(0, offset))
        if batch is None:
            raise HTTPException(404, "Lote desconhecido.")
        return batch

    @app.post("/v1/ingestion/batches/{batch_id}/cancel")
    def cancel(batch_id: str) -> dict[str, Any]:
        if repository.batch(batch_id, limit=0) is None:
            raise HTTPException(404, "Lote desconhecido.")
        return {"cancel_requested": repository.request_cancel(batch_id)}

    @app.post("/v1/ingestion/batches/{batch_id}/resume")
    def resume(batch_id: str) -> dict[str, Any]:
        resumed = repository.resume(batch_id)
        worker.notify()
        return {"resumed": resumed}

    @app.get("/v1/ingestion/documents")
    def documents() -> dict[str, Any]:
        items = repository.documents()
        return {"documents": [{k: d[k] for k in ("source_id", "path", "sha256", "kind", "original_url",
                                                  "extracted_at", "acquired_at", "language")}
                              | {"name": Path(d["path"]).name} for d in items]}

    @app.get("/v1/ingestion/documents/{source_id}")
    def document(source_id: str) -> dict[str, Any]:
        record = repository.document(source_id)
        if record is None:
            raise HTTPException(404, "Documento desconhecido.")
        path = Path(record["path"])
        try:
            data = path.read_bytes()
        except OSError:
            raise HTTPException(404, "O arquivo não está mais na pasta de documentos.") from None
        return {**record, "name": path.name, "truncated": len(data) > MAX_DOCUMENT_BYTES,
                "markdown": data[:MAX_DOCUMENT_BYTES].decode("utf-8", errors="replace")}

    @app.post("/v1/ingestion/shutdown")
    def shutdown() -> dict[str, Any]:
        if on_shutdown is not None:
            threading.Timer(0.2, on_shutdown).start()
        return {"stopping": True}

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse({"error": "request_failed", "message": str(exc.detail)}, status_code=exc.status_code)

    return app
