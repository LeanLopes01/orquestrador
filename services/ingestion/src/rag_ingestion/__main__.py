"""CLI da ingestão.

    python -m rag_ingestion --config .local/ingestion.toml doctor
    python -m rag_ingestion --config .local/ingestion.toml run --input fontes.txt --mode online
    python -m rag_ingestion --config .local/ingestion.toml run --input docs/catalogo-fontes-documentacao-rag.md
    python -m rag_ingestion --config .local/ingestion.toml resume BATCH_ID
    python -m rag_ingestion --config .local/ingestion.toml serve
    python -m rag_ingestion --config .local/ingestion.toml stop
    python -m rag_ingestion --config .local/ingestion.toml prune-cache

Exit codes de run: 0 sem falhas (skips documentados contam como sucesso do lote),
1 falha em algum item, 2 erro global de entrada/configuração.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

from .acquisition import prune_cache
from .config import ConfigError, IngestionConfig, load_config
from .events import EventLog
from .inputs import InputError, load_input
from .pipeline import Pipeline
from .process_lock import LockBusy, ProcessLock
from .repository import Repository


def _lock(config: IngestionConfig) -> ProcessLock:
    try:
        return ProcessLock(config.state_path.with_name("service.lock")).acquire()
    except LockBusy:
        raise SystemExit(
            "Outro processo da ingestão (provavelmente o serviço) possui o estado. "
            "Use a UI/endpoints ou pare o serviço antes de rodar comandos standalone."
        ) from None


def doctor(config: IngestionConfig) -> int:
    ok = True
    print(f"Configuração: {config.config_path}")
    for name in ("output_root", "state_path", "cache_root", "manifests_root", "token_path", "catalog_path"):
        value = getattr(config, name)
        print(f"  {name}: {value}")
    rag_toml = config.config_path.with_name("rag.toml")
    if rag_toml.exists():
        import tomllib

        data = tomllib.loads(rag_toml.read_text(encoding="utf-8-sig"))
        docs_root = data.get("docs_root")
        resolved = (rag_toml.parent / docs_root).resolve() if docs_root else None
        same = resolved == config.output_root
        ok &= same
        print(f"  docs_root do RAG: {resolved} -> {'igual ao destino' if same else 'DIVERGENTE do output_root'}")
    for module in ("trafilatura", "youtube_transcript_api", "fastapi", "uvicorn"):
        try:
            mod = __import__(module)
            print(f"  {module}: {getattr(mod, '__version__', 'ok')}")
        except ImportError:
            ok = False
            print(f"  {module}: AUSENTE")
    try:
        config.output_root.mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(config.output_root).free // (1024 * 1024)
        print(f"  espaço livre no destino: {free} MiB")
    except OSError as exc:
        ok = False
        print(f"  destino inacessível: {exc}")
    if config.catalog_path and config.catalog_path.exists():
        try:
            items = load_input(config.catalog_path)
            print(f"  catálogo: {len(items)} fontes habilitadas")
        except InputError as exc:
            ok = False
            print(f"  catálogo inválido: {exc}")
    print("OK" if ok else "Há problemas acima.")
    return 0 if ok else 1


def run(config: IngestionConfig, input_path: str, mode: str) -> int:
    try:
        items = load_input(input_path)
    except InputError as exc:
        print(f"Erro de entrada: {exc}", file=sys.stderr)
        return 2
    if not items:
        print("Nenhuma fonte habilitada na entrada.", file=sys.stderr)
        return 2
    with _lock(config):
        repository = Repository(config.state_path)
        repository.recover()
        events = EventLog(config.log_path, lambda e: print(f"[{e.stage}] {e.status}: {e.message}"))
        pipeline = Pipeline(config, repository, events)
        batch_id = repository.create_batch(config.project_id, mode, items, label=Path(input_path).name)
        report = pipeline.run_batch(batch_id)
        return _report(report)


def _report(report: dict) -> int:
    counts = report["counts"]
    print(f"\nLote {report['id']} · {report['state']}")
    print(f"  completed={counts['completed']} skipped={counts['skipped']} failed={counts['failed']}"
          f" cancelled={counts['cancelled']}")
    for item in report["items"]:
        result = item.get("result") or {}
        label = item.get("catalog_id") or item["raw_url"]
        print(f"  - {label}: {item['status']} {result.get('reason_code') or ''} {result.get('output_path') or ''}")
    if report.get("manifest_path"):
        print(f"Manifesto: {report['manifest_path']}")
    return 1 if counts["failed"] else 0


def _request(config: IngestionConfig, method: str, path: str) -> dict:
    token = config.token_path.read_text(encoding="ascii").strip()
    request = urllib.request.Request(
        f"http://127.0.0.1:{config.port}{path}", method=method,
        headers={"X-Local-Token": token, "Content-Type": "application/json"}, data=b"{}" if method == "POST" else None,
    )
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310 - loopback fixo
        return json.loads(response.read())


def serve(config: IngestionConfig) -> int:
    import uvicorn

    from .api import create_app

    with _lock(config):
        server: uvicorn.Server | None = None

        def stop() -> None:
            if server is not None:
                server.should_exit = True

        app = create_app(config, on_shutdown=stop)
        server = uvicorn.Server(uvicorn.Config(app, host=config.host, port=config.port, log_level="info",
                                               access_log=False, workers=1, reload=False))
        try:
            server.run()
        except OSError as exc:
            print(f"Não foi possível abrir {config.host}:{config.port}: {exc}", file=sys.stderr)
            return 3
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="rag_ingestion")
    parser.add_argument("--config", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    run_parser = commands.add_parser("run")
    run_parser.add_argument("--input", required=True)
    run_parser.add_argument("--mode", choices=["online", "offline"])
    resume_parser = commands.add_parser("resume")
    resume_parser.add_argument("batch_id")
    commands.add_parser("serve")
    commands.add_parser("stop")
    commands.add_parser("prune-cache")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"Erro de configuração: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    if args.command == "doctor":
        raise SystemExit(doctor(config))
    if args.command == "run":
        raise SystemExit(run(config, args.input, args.mode or config.default_mode))
    if args.command == "resume":
        with _lock(config):
            repository = Repository(config.state_path)
            repository.recover()
            if not repository.resume(args.batch_id):
                raise SystemExit("Lote inexistente ou não interrompido.")
            pipeline = Pipeline(config, repository, EventLog(config.log_path))
            raise SystemExit(_report(pipeline.run_batch(args.batch_id)))
    if args.command == "serve":
        raise SystemExit(serve(config))
    if args.command == "stop":
        try:
            _request(config, "POST", "/v1/ingestion/shutdown")
            print("Ingestão encerrando.")
        except (OSError, urllib.error.URLError):
            print("A ingestão não está em execução.")
        return
    if args.command == "prune-cache":
        with _lock(config):
            print(f"{prune_cache(config.cache_root)} revisões antigas removidas.")


if __name__ == "__main__":
    main()
