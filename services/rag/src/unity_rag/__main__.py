"""CLI do RAG local.

    python -m unity_rag --config .local/rag.toml doctor
    python -m unity_rag --config .local/rag.toml prepare-models      (download explícito, exige internet)
    python -m unity_rag --config .local/rag.toml index-code
    python -m unity_rag --config .local/rag.toml index-docs
    python -m unity_rag --config .local/rag.toml retrieve "Como NetworkManager usa Steamworks?"
    python -m unity_rag --config .local/rag.toml ask "Como a regra de movimento afeta o grid?"
    python -m unity_rag --config .local/rag.toml chat --watch
    python -m unity_rag --config .local/rag.toml watch
    python -m unity_rag --config .local/rag.toml serve               (UI/API; não rode junto do chat)
    python -m unity_rag --config .local/rag.toml stop

Comandos standalone recusam rodar se outro processo (o serviço) possuir a base.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import threading
import urllib.error
import urllib.request

from .config import ConfigError, RagConfig, apply_offline_environment, load_config


def _lock(config: RagConfig):
    from .process_lock import LockBusy, ProcessLock

    try:
        return ProcessLock(config.lock_path).acquire()
    except LockBusy:
        raise SystemExit(
            "Outro processo do RAG (provavelmente o serviço iniciado pelo helper) possui a base Chroma. "
            "Use a UI/endpoints (/api/rag) ou pare o serviço com `unity_rag stop`."
        ) from None


def doctor(config: RagConfig) -> int:
    apply_offline_environment(config)
    ok = True
    print(f"Configuração: {config.config_path}")
    for name in ("unity_project_root", "scripts_root", "docs_root", "chroma_path", "index_state_path", "token_path"):
        print(f"  {name}: {getattr(config, name)}")
    scripts = config.scripts_root.is_dir()
    ok &= scripts
    print(f"  Assets/Scripts acessível: {'sim' if scripts else 'NÃO'}")
    ingestion = config.config_path.with_name("ingestion.toml")
    if ingestion.exists():
        import tomllib

        data = tomllib.loads(ingestion.read_text(encoding="utf-8-sig"))
        out = (ingestion.parent / data.get("output_root", "")).resolve()
        same = out == config.docs_root
        ok &= same
        print(f"  output_root da ingestão: {out} -> {'igual ao docs_root' if same else 'DIVERGENTE'}")
    print(f"  modo offline: {config.offline}")
    import importlib

    for module in ("torch", "transformers", "sentence_transformers", "chromadb", "watchdog", "fastapi", "airllm"):
        try:
            mod = importlib.import_module(module)
            print(f"  {module}: {getattr(mod, '__version__', 'ok')}")
        except Exception as exc:  # noqa: BLE001 - diagnóstico
            ok = False
            print(f"  {module}: ERRO {type(exc).__name__}: {exc}")
    try:
        import torch

        print(f"  dispositivo: cuda={'sim' if torch.cuda.is_available() else 'não'}; gerador em {config.generator.device}")
    except ImportError:
        pass
    emb = config.embedding.local_dir
    has_emb = (emb / "modules.json").exists()
    ok &= has_emb
    print(f"  embeddings ({config.embedding.repo_id}): {'presentes' if has_emb else 'AUSENTES'} em {emb}")
    if config.generator.enabled and config.generator.model_path:
        from .airllm_engine import missing_assets

        missing = missing_assets(config.generator.model_path)
        print(f"  gerador ({config.generator.repo_id}): {'completo' if not missing else 'faltando ' + ', '.join(missing)}")
    else:
        print("  gerador: não configurado (busca/indexação continuam disponíveis)")
    target = config.chroma_path.parent
    target.mkdir(parents=True, exist_ok=True)
    print(f"  espaço livre em {target}: {shutil.disk_usage(target).free // (1024 ** 3)} GiB")
    print("OK" if ok else "Há problemas acima.")
    return 0 if ok else 1


def prepare_models(config: RagConfig) -> int:
    """Único comando que acessa a rede: baixa os modelos configurados para disco local."""
    from huggingface_hub import HfApi, snapshot_download

    api = HfApi()
    jobs = [(config.embedding.repo_id, config.embedding.local_dir,
             ["*.json", "*.txt", "model.safetensors", "sentencepiece.bpe.model", "1_Pooling/*", "tokenizer*"])]
    if config.generator.enabled and config.generator.model_path and config.generator.repo_id:
        jobs.append((config.generator.repo_id, config.generator.model_path, ["*.json", "*.txt", "*.safetensors", "LICENSE"]))
    for repo, target, patterns in jobs:
        sha = api.model_info(repo).sha
        print(f"Baixando {repo}@{sha[:10]} para {target}...")
        snapshot_download(repo, revision=sha, local_dir=target, allow_patterns=patterns)
        (target / "rag-model.json").write_text(json.dumps({"repo_id": repo, "revision": sha}, indent=2), encoding="utf-8")
    print("Modelos prontos. Os comandos seguintes rodam offline.")
    return 0


def _orchestrator(config: RagConfig, *, watch: bool):
    from .orchestrator import RagOrchestrator

    rag = RagOrchestrator(config, watch=watch)
    rag.start()
    if rag.embeddings_state != "ready":
        raise SystemExit(f"Embeddings indisponíveis: {rag.embeddings_error}")
    return rag


def _print_retrieval(result) -> None:
    for source in result.sources:
        extra = source.provenance.get("source_url") or source.provenance.get("main_class") or ""
        print(f"[{source.id}] {source.kind} {source.relpath} dist={source.distance:.3f} {source.state} {extra}")
    for warning in result.warnings:
        print(f"  aviso: {warning}")


def _ask(rag, query: str) -> None:
    def show(event) -> None:
        print(f"\r  {event.message} ({event.elapsed_ms / 1000:.0f}s)        ", end="", flush=True)

    result = rag.ask(query, show)
    print("\n\n" + result.answer + "\n")
    for source in result.sources:
        print(f"  [{source['id']}] {source['relpath']} ({source['scope']})")
    for warning in result.warnings:
        print(f"  aviso: {warning}")
    print(f"  modelo {result.model} · prompt {result.prompt_tokens} tokens · {result.generated_tokens} gerados"
          f" · {result.timings_ms.get('total', 0) / 1000:.0f}s")


def serve(config: RagConfig) -> int:
    import uvicorn

    from .api import create_app

    apply_offline_environment(config)
    with _lock(config):
        server: uvicorn.Server | None = None

        def stop() -> None:
            if server is not None:
                server.should_exit = True

        app = create_app(config, on_shutdown=stop)
        server = uvicorn.Server(uvicorn.Config(app, host=config.host, port=config.port, log_level="info",
                                               access_log=False, workers=1, reload=False))
        server.run()
        if not server.started:
            print(f"Não foi possível abrir {config.host}:{config.port} (porta ocupada?).", file=sys.stderr)
            return 3
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="unity_rag")
    parser.add_argument("--config", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("doctor", "prepare-models", "index-code", "index-docs", "watch", "serve", "stop"):
        commands.add_parser(name)
    for name in ("retrieve", "ask"):
        commands.add_parser(name).add_argument("query")
    chat = commands.add_parser("chat")
    chat.add_argument("--watch", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    for noisy in ("httpx", "chromadb", "sentence_transformers", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"Erro de configuração: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    command = args.command
    if command == "doctor":
        raise SystemExit(doctor(config))
    if command == "prepare-models":
        raise SystemExit(prepare_models(config))
    if command == "serve":
        raise SystemExit(serve(config))
    if command == "stop":
        try:
            token = config.token_path.read_text(encoding="ascii").strip()
            request = urllib.request.Request(f"http://127.0.0.1:{config.port}/v1/rag/shutdown", method="POST",
                                             headers={"X-Local-Token": token}, data=b"{}")
            urllib.request.urlopen(request, timeout=10).read()  # noqa: S310 - loopback fixo
            print("RAG encerrando (o helper Jarvis Desktop encerra junto).")
        except (OSError, urllib.error.URLError):
            print("O RAG não está em execução.")
        return
    with _lock(config):
        rag = _orchestrator(config, watch=command in {"watch"} or (command == "chat" and args.watch))
        try:
            if command == "index-code":
                print(json.dumps(rag.submit_index("code").result()["code"], ensure_ascii=False, indent=2))
            elif command == "index-docs":
                print(json.dumps(rag.submit_index("documents").result()["documents"], ensure_ascii=False, indent=2))
            elif command == "retrieve":
                _print_retrieval(rag.retrieve(args.query))
            elif command == "ask":
                _ask(rag, args.query)
            elif command == "watch":
                print("Observando scripts. Ctrl+C para sair.")
                threading.Event().wait()
            elif command == "chat":
                print("Pergunte sobre o DiceVTT (linha vazia sai).")
                while True:
                    try:
                        query = input("> ").strip()
                    except EOFError:
                        break
                    if not query:
                        break
                    if query.startswith("/buscar "):
                        _print_retrieval(rag.retrieve(query[8:]))
                    else:
                        _ask(rag, query)
        except KeyboardInterrupt:
            pass
        finally:
            rag.close()


if __name__ == "__main__":
    main()
