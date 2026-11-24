from __future__ import annotations

import subprocess
import sys
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest

from dicevtt_diagnostics import unity_process
from dicevtt_diagnostics.collectors import full
from dicevtt_diagnostics.collectors.base import Cancelled, CheckResult, Context
from dicevtt_diagnostics.config import FullAudit, Validator
from dicevtt_diagnostics.jobs import Runner
from dicevtt_diagnostics.settings import SettingsStore
from dicevtt_diagnostics.store import AuditStore

FAKE = Path(__file__).with_name("fake_unity.py")


@pytest.fixture()
def setup(config, project, tmp_path, monkeypatch):
    (project / "ProjectSettings" / "ProjectSettings.asset").write_text(
        "PlayerSettings:\n  companyName: DiceVTT inc\n  productName: DiceVTT\n", encoding="utf-8")
    local_low = tmp_path / "LocalLow"
    (local_low / "DiceVTT inc" / "DiceVTT" / "sistemas" / "zinefastus-srd").mkdir(parents=True)
    (local_low / "DiceVTT inc" / "DiceVTT" / "sistemas" / "zinefastus-srd" / "sistema.json").write_text("{}")
    monkeypatch.setattr(full, "_local_low", lambda: local_low)
    monkeypatch.setattr(full, "unity_command", lambda _ctx: [sys.executable, str(FAKE)])
    validators = (Validator("ok", "Ok", "Ok.Run", "-relatorioOk"), Validator("falha", "Falha", "Falha.Run", "-r"),
                  Validator("sem", "Sem relatório", "Sem.Relatorio", "-r"))
    cfg = replace(config, full=FullAudit(audit_root=tmp_path / "audit", provision=("sistemas",),
                                         validators=validators, unity_timeout_seconds=600))
    return cfg, project, local_low


def make_ctx(cfg, tmp_path, run_id="AUD-20261025-000000-aaaaaa"):
    ctx = Context(cfg, threading.Event(), time.monotonic() + 60, tmp_path / "runs" / run_id)
    ctx.full_deadline = time.monotonic() + 600
    ctx.shared["editor_path"] = "fake"
    return ctx


def run_check(fn, ctx, cid="x"):
    check = CheckResult(cid, cid)
    fn(ctx, check)
    return check


def test_snapshot_isolates_data_and_never_touches_user_data(setup, tmp_path):
    cfg, project, local_low = setup
    ctx = make_ctx(cfg, tmp_path)
    check = run_check(full.prepare_snapshot, ctx)
    session = ctx.shared["full_session"]
    assert check.data["files"] >= 4 and check.data["library_source"] == "cold"
    patched = (session.project / "ProjectSettings" / "ProjectSettings.asset").read_text(encoding="utf-8")
    assert "productName: DiceVTT-Audit" in patched
    assert "productName: DiceVTT\n" in (project / "ProjectSettings" / "ProjectSettings.asset").read_text()
    assert (local_low / "DiceVTT inc" / "DiceVTT-Audit" / "sistemas" / "zinefastus-srd" / "sistema.json").exists()
    for cleanup in ctx.cleanups:
        cleanup()
    assert not session.root.exists()
    assert not (local_low / "DiceVTT inc" / "DiceVTT-Audit").exists()
    assert (local_low / "DiceVTT inc" / "DiceVTT" / "sistemas" / "zinefastus-srd" / "sistema.json").exists()


def test_validators_outcomes_are_distinct(setup, tmp_path):
    cfg, _, _ = setup
    ctx = make_ctx(cfg, tmp_path)
    run_check(full.prepare_snapshot, ctx)
    compile_check = run_check(full.import_and_compile, ctx)
    assert ctx.shared["full_session"].compiled and compile_check.status == "collected"
    check = run_check(full.run_validators, ctx)
    outcomes = {o["id"]: o["status"] for o in check.data["validators"]}
    assert outcomes == {"ok": "passed", "falha": "failed", "sem": "error"}
    assert [f.rule for f in check.findings] == ["validator.failure"]
    assert "#" in check.findings[0].key  # números normalizados: identidade estável entre runs
    assert check.status == "partial"
    for cleanup in ctx.cleanups:
        cleanup()
    assert (cfg.full.audit_root / "cache" / "Library").is_dir()  # a Library volta para o cache
    assert (ctx.run_dir / "full" / "falha.txt").exists()


def test_compile_errors_skip_validators_and_license_is_environment_error(setup, tmp_path, project):
    cfg, _, _ = setup
    (project / "Assets" / "quebrado.txt").write_text("x")
    ctx = make_ctx(cfg, tmp_path)
    run_check(full.prepare_snapshot, ctx)
    compile_check = run_check(full.import_and_compile, ctx)
    assert [f.rule for f in compile_check.findings] == ["isolated.compile-error"]
    assert run_check(full.run_validators, ctx).status == "skipped"
    (project / "Assets" / "quebrado.txt").unlink()
    cfg2 = replace(cfg, full=replace(cfg.full, validators=(Validator("lic", "Licença", "Licenca.Run", "-r"),)))
    ctx2 = make_ctx(cfg2, tmp_path, "AUD-20261025-000001-bbbbbb")
    run_check(full.prepare_snapshot, ctx2)
    # O run anterior não passou pela limpeza: a Library que ficou na cópia dele é recuperada como cache.
    assert ctx2.shared["full_session"].library_source == "cache"
    run_check(full.import_and_compile, ctx2)
    check = run_check(full.run_validators, ctx2)
    assert check.data["validators"][0]["note"] == "licença indisponível" and check.status == "error"
    assert check.findings == []


def test_timeout_kills_only_the_job_process(setup, tmp_path):
    cfg, _, _ = setup
    bystander = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        cfg = replace(cfg, full=replace(cfg.full, validators=(Validator("trava", "Trava", "Trava.Run", "-r",
                                                                        timeout_seconds=2),)))
        ctx = make_ctx(cfg, tmp_path)
        run_check(full.prepare_snapshot, ctx)
        run_check(full.import_and_compile, ctx)
        monkey_min = full.MIN_STEP_SECONDS
        full.MIN_STEP_SECONDS = 1
        try:
            started = time.monotonic()
            check = run_check(full.run_validators, ctx)
        finally:
            full.MIN_STEP_SECONDS = monkey_min
        assert time.monotonic() - started < 30
        assert check.data["validators"][0]["status"] == "timeout"
        assert bystander.poll() is None  # o processo alheio continua vivo
    finally:
        bystander.kill()


def test_cancel_stops_unity_run_promptly(tmp_path):
    cancel = threading.Event()
    threading.Timer(1.0, cancel.set).start()
    started = time.monotonic()
    with pytest.raises(Cancelled):
        unity_process.run_unity([sys.executable, "-c", "import time; time.sleep(60)"], tmp_path / "x.log", 120,
                                cancel, tmp_path)
    assert time.monotonic() - started < 15


@pytest.mark.parametrize(("mode", "expected"), [("zero", "tests.zero"), ("falha", "tests.failed"), ("sem-xml", None)])
def test_editmode_outcomes(setup, tmp_path, project, mode, expected):
    cfg, _, _ = setup
    (project / "Assets" / "modo_testes.txt").write_text(mode)
    ctx = make_ctx(cfg, tmp_path)
    ctx.shared["test_assemblies"] = ["Assets/Tests/Tests.asmdef"]
    run_check(full.prepare_snapshot, ctx)
    run_check(full.import_and_compile, ctx)
    check = run_check(full.editmode_tests, ctx)
    if expected is None:
        assert check.status == "error" and check.findings == []  # sem XML não é aprovação
    else:
        assert expected in [f.rule for f in check.findings]


def test_no_test_assembly_is_skipped_not_passed(setup, tmp_path):
    cfg, _, _ = setup
    ctx = make_ctx(cfg, tmp_path)
    check = run_check(full.editmode_tests, ctx)
    assert check.status == "skipped" and "não é aprovação" in check.note


def test_origin_integrity_detects_parallel_edits(setup, tmp_path, project):
    cfg, _, _ = setup
    ctx = make_ctx(cfg, tmp_path)
    run_check(full.prepare_snapshot, ctx)
    assert run_check(full.origin_integrity, ctx).data["identical"] is True
    (project / "Assets" / "Scripts" / "A.cs").write_text("class A { int x; }", encoding="utf-8")
    check = run_check(full.origin_integrity, ctx)
    assert check.data["identical"] is False and check.findings[0].rule == "audit.origin-changed"


def test_full_profile_end_to_end_through_runner(setup):
    cfg, _, _ = setup
    store = AuditStore(cfg.state_path)
    runner = Runner(cfg, store, SettingsStore(cfg.settings_path))
    result = runner.submit("full-manual-0001", "manual", "full-audit")
    assert result["profile"] == "full-audit"
    runner.execute(result["run_id"])
    run = store.run(result["run_id"])
    checks = {c["id"]: c["status"] for c in run["checks"]}
    assert checks["snapshot"] == "collected" and checks["isolated_compile"] == "collected"
    assert checks["validators"] == "partial" and checks["origin_integrity"] == "collected"
    assert not (cfg.full.audit_root / "snapshots" / result["run_id"]).exists()
    store.close()
