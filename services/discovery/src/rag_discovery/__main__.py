"""CLI da descoberta automática de fontes.

    python -m rag_discovery doctor
    python -m rag_discovery plan [--no-llm] [--refresh]       # só mostra o que seria coletado
    python -m rag_discovery run  [--no-llm] [--no-index]      # coleta e indexa
    python -m rag_discovery list [--status proposed|submitted|ingested|failed|skipped|rejected]
    python -m rag_discovery reject URL_OU_SOURCE_ID ...

`--config` padrão: .local/discovery.toml (a partir da raiz do Orquestrador).
Exit codes: 0 ok, 1 alguma fonte falhou ou serviço offline, 2 erro de configuração.
"""

from __future__ import annotations

import argparse
import sys

from dataclasses import replace
from pathlib import Path

from rag_ingestion.process_lock import LockBusy, ProcessLock

from .config import ConfigError, DiscoveryConfig, load_config
from .local_corpus import DEFAULT_VAULT, import_local_corpus
from .runner import build_plan, submit
from .services import LocalService, ServiceError
from .state import Store


def _print_plan(plan) -> None:
    if not plan.candidates:
        print("\nNada novo para coletar: o RAG já cobre o que foi encontrado.")
        return
    print(f"\n{len(plan.candidates)} fontes novas:")
    for c in plan.candidates:
        print(f"  [{c.strategy:8}] {c.score:>6}  {c.title[:70]}")
        print(f"             {c.url}")
        print(f"             {c.reason}")


def doctor(config: DiscoveryConfig) -> int:
    from rag_ingestion.config import load_config as load_ingestion
    from unity_rag.airllm_engine import missing_assets
    from unity_rag.config import load_config as load_rag

    ok = True
    print(f"Configuração: {config.config_path}")
    try:
        ingestion, rag = load_ingestion(config.ingestion_config), load_rag(config.rag_config)
    except Exception as exc:
        print(f"  configs da ingestão/RAG inválidas: {exc}")
        return 2
    print(f"  scripts: {rag.scripts_root} ({'ok' if rag.scripts_root.is_dir() else 'AUSENTE'})")
    ok &= rag.scripts_root.is_dir()
    print(f"  embeddings: {rag.embedding.local_dir}")
    if rag.generator.model_path:
        missing = missing_assets(rag.generator.model_path)
        print(f"  AirLLM: {rag.generator.model_path.name} -> {'ok' if not missing else 'faltando ' + ', '.join(missing)}")
    else:
        print("  AirLLM: sem gerador configurado (só estratégia por código e tópicos fixos)")
    for name, cfg, health in (("ingestão", ingestion, "/v1/ingestion/health"), ("RAG", rag, "/v1/rag/health")):
        online = LocalService(name, cfg.host, cfg.port, cfg.token_path).online(health)
        ok &= online
        print(f"  serviço {name} {cfg.host}:{cfg.port}: {'online' if online else 'offline (ligue com iniciar-tudo.cmd)'}")
    print(f"  catálogos: {', '.join(c.id for c in config.catalogs)}")
    store = Store(config.state_path)
    print(f"  estado: {store.counts() or 'vazio'}")
    store.close()
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rag_discovery", description="Descoberta automática de fontes para o RAG.")
    parser.add_argument("--config", default=".local/discovery.toml")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    for name in ("plan", "run"):
        sub = commands.add_parser(name)
        sub.add_argument("--no-llm", action="store_true", help="não usa o AirLLM para sugerir tópicos")
        sub.add_argument("--refresh", action="store_true", help="baixa os índices mesmo com cache válido")
        sub.add_argument("--max-api", type=int, default=None, help="sobrescreve max_api_per_run nesta execução")
        sub.add_argument("--max-topic", type=int, default=None, help="sobrescreve max_topic_per_run nesta execução")
        if name == "run":
            sub.add_argument("--no-index", action="store_true", help="não pede a indexação ao RAG no fim")
    local_cmd = commands.add_parser("import-local", help="importa SRD 5e XML e notas Markdown do vault para o RAG")
    local_cmd.add_argument("--vault", default=str(DEFAULT_VAULT), help="caminho do vault local")
    local_cmd.add_argument("--no-index", action="store_true", help="não pede a indexação ao RAG no fim")
    listing = commands.add_parser("list")
    listing.add_argument("--status")
    listing.add_argument("--limit", type=int, default=50)
    reject = commands.add_parser("reject")
    reject.add_argument("items", nargs="+")
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2
    if args.command == "doctor":
        return doctor(config)
    if args.command == "import-local":
        import_local_corpus(config, vault_root=Path(args.vault), index=not args.no_index)
        return 0

    if getattr(args, "max_api", None) is not None:
        config = replace(config, max_api_per_run=max(0, args.max_api))
    if getattr(args, "max_topic", None) is not None:
        config = replace(config, max_topic_per_run=max(0, args.max_topic))

    store = Store(config.state_path)
    try:
        if args.command == "list":
            for row in store.candidates(args.status, args.limit):
                print(f"{row['status']:9} [{row['strategy']:8}] {row['title'][:60]}  {row['url']}"
                      + (f"  ({row['detail']})" if row["detail"] else ""))
            print(store.counts())
            return 0
        if args.command == "reject":
            changed = sum(store.reject(item) for item in args.items)
            print(f"{changed} fonte(s) marcadas como rejeitadas; não serão propostas de novo.")
            return 0

        try:
            lock = ProcessLock(config.state_path.with_name("discovery.lock")).acquire()
        except LockBusy:
            print("Outra descoberta já está rodando.", file=sys.stderr)
            return 1
        with lock:
            plan = build_plan(config, store, use_llm=not args.no_llm, refresh=args.refresh)
            for warning in plan.warnings:
                print(f"aviso: {warning}")
            store.start_run(plan.run_id)
            store.propose(plan.run_id, plan.candidates)
            _print_plan(plan)
            if args.command == "plan":
                store.finish_run(plan.run_id, "planned", f"{len(plan.candidates)} propostas")
                return 0
            try:
                totals = submit(config, store, plan, index=not args.no_index)
            except ServiceError as exc:
                store.finish_run(plan.run_id, "failed", str(exc))
                print(f"erro: {exc}", file=sys.stderr)
                return 1
            store.finish_run(plan.run_id, "completed", repr(totals))
            print(f"\nResultado: {totals or 'nada enviado'}")
            return 1 if totals.get("failed") else 0
    finally:
        store.close()


if __name__ == "__main__":
    sys.exit(main())
