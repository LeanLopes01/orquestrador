"""Fila serial de auditorias: um worker, prazo por perfil e cancelamento cooperativo.

Pedidos de abertura respeitam `on_startup` da configuração real; desativado vira registro
explícito, nunca relatório inventado.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import collectors, report
from .collectors.base import Cancelled, CheckResult, Context, sha256_bytes, utc_now
from .config import DiagnosticsConfig
from .settings import PROFILES, SettingsError, SettingsStore
from .store import AuditStore, now

logger = logging.getLogger("dicevtt_diagnostics")
TRIGGERS = ("startup", "manual")


class SubmitError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _write(path: Path, data: bytes) -> str:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    return sha256_bytes(data)


def revision_of(vcs: CheckResult | None) -> dict[str, Any]:
    data = vcs.data if vcs else {}
    plastic = data.get("plastic") or {}
    return {
        "vcs": data.get("vcs"), "source_state": data.get("source_state", "working_tree"),
        "git_root": data.get("git_root"), "project_relative_path": data.get("project_relative_path"),
        "commit": data.get("commit"), "branch": data.get("branch"),
        "dirty": data.get("dirty"),
        "plastic": {k: plastic.get(k) for k in ("repository", "branch", "changeset", "pending", "private")}
        if plastic else None,
    }


class Runner:
    def __init__(self, config: DiagnosticsConfig, store: AuditStore, settings: SettingsStore) -> None:
        self.config = config
        self.store = store
        self.settings = settings
        self.current: str | None = None
        self.on_finished: Callable[[str, str], None] | None = None  # ex.: investigação por IA
        self._cancel = threading.Event()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="audit-worker", daemon=True)

    def start(self) -> None:
        recovered = self.store.recover()
        if recovered:
            logger.warning("%s auditoria(s) marcadas como interrupted após reinício", recovered)
        self._thread.start()

    def stop(self, timeout: float = 15) -> None:
        self._stop.set()
        self._cancel.set()
        self._wake.set()
        self._thread.join(timeout=timeout)

    # Pedidos ---------------------------------------------------------------------------------

    def submit(self, key: str, trigger: str, profile: str | None = None) -> dict[str, Any]:
        """A abertura usa o perfil das preferências; um pedido manual pode escolher outro."""
        if trigger not in TRIGGERS:
            raise SubmitError("invalid_trigger", f"trigger deve ser {' ou '.join(TRIGGERS)}.")
        if profile is not None and (trigger != "manual" or profile not in PROFILES):
            raise SubmitError("invalid_profile", "profile só vale em pedidos manuais: startup-light ou full-audit.")
        try:
            settings = self.settings.load()
        except SettingsError as exc:
            raise SubmitError("settings_unreadable", str(exc)) from None
        chosen = profile or settings.profile
        if trigger == "startup" and not settings.on_startup:
            result = self.store.record_disabled(key, trigger)
        else:
            planned = collectors.plan(chosen, self.config.full is not None)
            result = self.store.request(key, self.config.project_id, chosen, trigger, len(planned))
        self._wake.set()
        return {**result, "profile": chosen, "settings_revision": settings.revision}

    def cancel(self, run_id: str) -> dict[str, Any]:
        if self.store.cancel_queued(run_id):
            return {"cancelled": True, "state": "cancelled"}
        if self.current == run_id:
            self._cancel.set()  # o coletor para no próximo ponto de verificação
            return {"cancelled": True, "state": "cancelling"}
        run = self.store.run(run_id)
        return {"cancelled": False, "state": run["state"] if run else None}

    # Execução --------------------------------------------------------------------------------

    def _loop(self) -> None:
        while not self._stop.is_set():
            row = self.store.next_queued()
            if row is None:
                self._wake.wait(5)
                self._wake.clear()
                continue
            self.current = row["id"]
            self._cancel.clear()
            try:
                self.execute(row["id"])
            except Exception:
                logger.exception("auditoria %s falhou", row["id"])
                self.store.fail(row["id"], "failed", "Erro interno do runner; veja audits/logs/service.log.")
            finally:
                self.current = None

    def execute(self, run_id: str) -> None:
        if not self.store.start(run_id):
            return
        run = self.store.run(run_id)
        assert run is not None
        run_dir = self.config.runs_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        light_deadline = time.monotonic() + self.config.light_deadline_seconds
        ctx = Context(self.config, self._cancel, light_deadline, run_dir)
        checks: list[CheckResult] = []
        try:
            for position, planned in enumerate(collectors.plan(run["profile"], self.config.full is not None)):
                check = CheckResult(planned.id, planned.name, started_at=utc_now())
                if planned.budget == "full" and not ctx.full_deadline and self.config.full is not None:
                    ctx.full_deadline = time.monotonic() + self.config.full.deadline_seconds
                    ctx.deadline = ctx.full_deadline
                if planned.collect is None:
                    check.status, check.note = "skipped", planned.skip_reason
                elif planned.budget == "light" and time.monotonic() > light_deadline:
                    check.status = "skipped"
                    check.note = f"Prazo do perfil ({self.config.light_deadline_seconds:.0f} s) esgotado antes deste check."
                elif planned.budget == "full" and ctx.remaining() <= 0:
                    check.status = "skipped"
                    check.note = f"Prazo do perfil completo ({self.config.full.deadline_seconds:.0f} s) esgotado."
                else:
                    started = time.monotonic()
                    try:
                        planned.collect(ctx, check)
                    except Cancelled:
                        raise
                    except Exception as exc:  # um coletor quebrado não derruba os outros
                        logger.exception("check %s falhou", planned.id)
                        check.degrade("error", f"{type(exc).__name__}: {exc}")
                    check.duration_ms = int((time.monotonic() - started) * 1000)
                    if check.status == "error" and not check.note:
                        check.note = check.problems[-1] if check.problems else "Falha na coleta."
                checks.append(check)
                self.store.save_check(run_id, position, check.to_dict())
        except Cancelled:
            self._cleanup(ctx, run_id, checks)
            if self._stop.is_set():  # helper/serviço encerrando, não um pedido do usuário
                self.store.fail(run_id, "interrupted", "O serviço foi encerrado durante a coleta; "
                                                       "checks concluídos foram preservados.")
            else:
                self.store.fail(run_id, "cancelled", "Cancelado a pedido; checks concluídos foram preservados.")
            return
        except BaseException:
            self._cleanup(ctx, run_id, checks)
            raise
        self._cleanup(ctx, run_id, checks)
        self._finish(run, run_dir, checks)

    def _cleanup(self, ctx: Context, run_id: str, checks: list[CheckResult]) -> None:
        """Limpezas da auditoria completa (cópia, cache da Library, dados isolados), sempre."""
        for cleanup in reversed(ctx.cleanups):
            try:
                cleanup()
            except Exception as exc:
                logger.exception("limpeza falhou")
                ctx.shared.setdefault("cleanup_errors", []).append(f"{type(exc).__name__}: {exc}")
        ctx.cleanups.clear()
        errors = ctx.shared.get("cleanup_errors") or []
        if errors and checks:
            checks[-1].problems.append("Limpeza incompleta da auditoria completa: " + "; ".join(errors))
            self.store.save_check(run_id, len(checks) - 1, checks[-1].to_dict())

    def _finish(self, run: dict[str, Any], run_dir: Path, checks: list[CheckResult]) -> None:
        statuses = {c.id: c.status for c in checks}
        current = [(c.id, f) for c in checks for f in c.findings]
        previous_id, previous = self.store.previous_findings(run["project"], run["profile"], run["id"])
        findings = report.compare(current, statuses, previous)
        state = report.run_state(checks)
        revision = revision_of(next((c for c in checks if c.id == "vcs"), None))
        try:
            settings_revision = self.settings.load().revision
        except SettingsError:
            settings_revision = -1
        run = {**run, "finished_at": now()}
        doc = report.build(run, checks, findings, revision, previous_id, state, settings_revision)
        raw_json = json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8")
        raw_html = report.render_html(doc).encode("utf-8")
        artifacts = [
            {"kind": "json", "name": "report.json", "sha256": _write(run_dir / "report.json", raw_json),
             "bytes": len(raw_json)},
            {"kind": "html", "name": "report.html", "sha256": _write(run_dir / "report.html", raw_html),
             "bytes": len(raw_html)},
        ]
        self.store.finalize(run["id"], state, doc["summary"], revision, findings, artifacts, run["finished_at"])
        logger.info("auditoria %s: %s, %s ocorrência(s)", run["id"], state, doc["summary"]["findings"])
        if self.on_finished is not None:
            try:
                self.on_finished(run["id"], state)
            except Exception:  # a investigação nunca invalida o relatório já salvo
                logger.exception("pós-auditoria falhou para %s", run["id"])
