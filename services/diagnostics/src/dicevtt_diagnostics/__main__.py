"""CLI do runner de relatórios.

    python -m dicevtt_diagnostics --config .local/diagnostics.toml doctor
    python -m dicevtt_diagnostics --config .local/diagnostics.toml serve            # o helper já faz isso
    python -m dicevtt_diagnostics --config .local/diagnostics.toml stop
    python -m dicevtt_diagnostics --config .local/diagnostics.toml run              # avulso, sem o serviço
    python -m dicevtt_diagnostics --config .local/diagnostics.toml request-startup  # chamado pelo iniciar-tudo.cmd

request-startup nunca bloqueia a interface: cria um startup_id UMA vez, espera o health por até
30 s e faz no máximo duas tentativas de POST (5 s cada) com a mesma chave. Tudo vai para
audits/logs/startup.log. Exit 0 aceito/desativado, 1 falhou.
"""

from __future__ import annotations

import argparse
import json
import logging
import logging.handlers
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime

from .config import ConfigError, DiagnosticsConfig, load_config
from .process_lock import LockBusy, ProcessLock

HEALTH_WAIT_SECONDS = 30
POST_TIMEOUT_SECONDS = 5
POST_ATTEMPTS = 2


def _lock(config: DiagnosticsConfig) -> ProcessLock:
    try:
        return ProcessLock(config.state_path.with_name("service.lock")).acquire()
    except LockBusy:
        raise SystemExit("O serviço de relatórios está ativo. Use a UI ou request-startup.") from None


def _request(config: DiagnosticsConfig, method: str, path: str, body: dict | None = None,
             headers: dict | None = None, timeout: float = 5) -> tuple[int, dict]:
    token = config.token_path.read_text(encoding="ascii").strip()
    request = urllib.request.Request(
        f"http://127.0.0.1:{config.port}{path}", method=method,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={"X-Local-Token": token, "Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - loopback fixo
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read() or b"{}")
        except ValueError:
            return exc.code, {}


def request_startup(config: DiagnosticsConfig) -> int:
    config.log_dir.mkdir(parents=True, exist_ok=True)
    log_path = config.log_dir / "startup.log"
    startup_id = str(uuid.uuid4())

    def log(message: str) -> None:
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{datetime.now().astimezone().isoformat(timespec='seconds')} {startup_id} {message}\n")

    log("pedido de relatório na abertura")
    deadline = time.monotonic() + HEALTH_WAIT_SECONDS
    while True:
        try:
            status, _ = _request(config, "GET", "/v1/diagnostics/health", timeout=3)
            if status == 200:
                break
        except (OSError, urllib.error.URLError, ValueError):
            pass
        if time.monotonic() >= deadline:
            log(f"runner não respondeu em {HEALTH_WAIT_SECONDS} s; nenhum relatório solicitado")
            return 1
        time.sleep(1)
    body = {"project": config.project_name, "trigger": "startup", "startup_id": startup_id, "auto_fix": False}
    for attempt in range(1, POST_ATTEMPTS + 1):
        try:
            status, data = _request(config, "POST", "/v1/audits", body, {"Idempotency-Key": startup_id},
                                    timeout=POST_TIMEOUT_SECONDS)
        except (OSError, urllib.error.URLError, ValueError) as exc:
            log(f"tentativa {attempt}: {type(exc).__name__}: {exc}")
            continue
        if status in (200, 202):
            log(f"aceito: {data.get('outcome')} run={data.get('run_id')} perfil={data.get('profile')}")
            return 0
        log(f"tentativa {attempt}: HTTP {status} {data.get('message') or data}")
        if status < 500:
            return 1  # recusa definitiva: repetir não muda a resposta
    return 1


def doctor(config: DiagnosticsConfig) -> int:
    print(f"Configuração: {config.config_path}")
    ok = config.project_root.is_dir()
    print(f"  projeto: {config.project_root} -> {'ok' if ok else 'AUSENTE'}")
    for name in ("state_path", "settings_path", "runs_root", "log_dir", "token_path"):
        print(f"  {name}: {getattr(config, name)}")
    for name in ("plastic_cm", "unity_editors", "editor_log", "player_log_dir"):
        value = getattr(config, name)
        print(f"  {name}: {value} -> {'ok' if value and value.exists() else 'não encontrado'}")
    print(f"  rag: {'porta ' + str(config.rag.port) if config.rag else 'não configurado'}")
    print(f"  porta do serviço: {config.host}:{config.port}")
    print("OK" if ok else "Há problemas acima.")
    return 0 if ok else 1


def run_once(config: DiagnosticsConfig) -> int:
    from .jobs import Runner
    from .settings import SettingsStore
    from .store import AuditStore

    with _lock(config):
        store = AuditStore(config.state_path)
        runner = Runner(config, store, SettingsStore(config.settings_path))
        store.recover()
        result = runner.submit(f"cli-{uuid.uuid4()}", "manual")
        runner.execute(result["run_id"])
        run = store.run(result["run_id"])
        print(json.dumps({k: run[k] for k in ("id", "state", "summary", "error")}, ensure_ascii=False, indent=2))
        print(f"Relatório: {config.runs_root / result['run_id'] / 'report.html'}")
        store.close()
        return 0 if run["state"] in ("completed", "partial") else 1


def serve(config: DiagnosticsConfig) -> int:
    import uvicorn

    from .api import create_app

    config.log_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(config.log_dir / "runner.log", maxBytes=2_000_000,
                                                   backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logging.getLogger("dicevtt_diagnostics").addHandler(handler)
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
    parser = argparse.ArgumentParser(prog="dicevtt_diagnostics")
    parser.add_argument("--config", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("doctor", "serve", "stop", "run", "request-startup"):
        commands.add_parser(name)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"Erro de configuração: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    if args.command == "doctor":
        raise SystemExit(doctor(config))
    if args.command == "serve":
        raise SystemExit(serve(config))
    if args.command == "run":
        raise SystemExit(run_once(config))
    if args.command == "request-startup":
        raise SystemExit(request_startup(config))
    if args.command == "stop":
        try:
            _request(config, "POST", "/v1/diagnostics/shutdown", {})
            print("Runner de relatórios encerrando.")
        except (OSError, urllib.error.URLError):
            print("O runner de relatórios não está em execução.")


if __name__ == "__main__":
    main()
