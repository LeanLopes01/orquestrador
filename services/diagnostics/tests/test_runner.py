from __future__ import annotations

import json
import threading

import pytest

from dicevtt_diagnostics import collectors
from dicevtt_diagnostics.collectors import PlannedCheck
from dicevtt_diagnostics.collectors.base import Finding
from dicevtt_diagnostics.jobs import Runner
from dicevtt_diagnostics.settings import SettingsStore
from dicevtt_diagnostics.store import AuditStore


@pytest.fixture()
def runner(config):
    store = AuditStore(config.state_path)
    yield Runner(config, store, SettingsStore(config.settings_path))
    store.close()


def fake_plan(findings_by_check, statuses=None):
    statuses = statuses or {}

    def make(check_id):
        def collect(_ctx, check):
            check.findings.extend(findings_by_check.get(check_id, []))
            if statuses.get(check_id):
                check.degrade(statuses[check_id], "simulado")
        return collect

    return lambda _profile, _full=True: [PlannedCheck("a", "Check A", make("a"), "light"),
                                        PlannedCheck("b", "Check B", make("b"), "light")]


def finding(key, summary="Achado"):
    return Finding(rule="teste.regra", severity="medium", state="confirmed", key=key, summary=summary)


def test_idempotent_coalesced_and_new_after_finish(runner, monkeypatch):
    monkeypatch.setattr(collectors, "plan", fake_plan({}))
    first = runner.submit("startup-key-0001", "startup")
    assert first["outcome"] == "created" and not first["duplicate"]
    again = runner.submit("startup-key-0001", "startup")
    assert again["duplicate"] and again["run_id"] == first["run_id"]
    other = runner.submit("startup-key-0002", "startup")
    assert other["outcome"] == "coalesced" and other["run_id"] == first["run_id"]
    runner.execute(first["run_id"])
    assert runner.store.run(first["run_id"])["startup_ids"] == ["startup-key-0001", "startup-key-0002"]
    third = runner.submit("startup-key-0003", "startup")
    assert third["outcome"] == "created" and third["run_id"] != first["run_id"]  # mesmo commit, novo relatório


def test_concurrent_requests_create_one_active_run(runner, monkeypatch):
    monkeypatch.setattr(collectors, "plan", fake_plan({}))
    results = []
    threads = [threading.Thread(target=lambda i=i: results.append(runner.submit(f"double-click-{i:04d}", "startup")))
               for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len({r["run_id"] for r in results}) == 1
    assert sorted(r["outcome"] for r in results).count("created") == 1


def test_disabled_startup_records_without_report(runner, config):
    runner.settings.save({"on_startup": False, "profile": "startup-light", "sync_to_server": False,
                          "investigate_with_ai": False, "workflow_url": ""}, 0)
    result = runner.submit("startup-disabled-1", "startup")
    assert result == {**result, "outcome": "disabled", "run_id": None}
    assert runner.store.runs()["items"] == []
    assert runner.store.last_startup()["outcome"] == "disabled"
    assert runner.submit("manual-allowed-01", "manual")["outcome"] == "created"  # manual continua possível


def test_restart_marks_active_runs_interrupted(runner, monkeypatch):
    monkeypatch.setattr(collectors, "plan", fake_plan({}))
    run_id = runner.submit("will-be-lost-01", "startup")["run_id"]
    runner.store.start(run_id)
    assert runner.store.recover() == 1
    assert runner.store.run(run_id)["state"] == "interrupted"


def test_cancel_queued(runner, monkeypatch):
    monkeypatch.setattr(collectors, "plan", fake_plan({}))
    run_id = runner.submit("cancel-me-0001", "manual")["run_id"]
    assert runner.cancel(run_id)["state"] == "cancelled"
    runner.execute(run_id)  # não roda depois de cancelado
    assert runner.store.run(run_id)["state"] == "cancelled"


def test_comparison_resolved_only_when_rechecked(runner, monkeypatch, config):
    monkeypatch.setattr(collectors, "plan", fake_plan({"a": [finding("x")], "b": [finding("y")]}))
    first = runner.submit("compare-run-01", "manual")["run_id"]
    runner.execute(first)
    # Segundo run: "x" sumiu com o check A coletado (resolvido); "y" sumiu mas B ficou parcial.
    monkeypatch.setattr(collectors, "plan", fake_plan({}, {"b": "partial"}))
    second = runner.submit("compare-run-02", "manual")["run_id"]
    runner.execute(second)
    doc = json.loads((config.runs_root / second / "report.json").read_text(encoding="utf-8"))
    by_check = {f["check_id"]: f["comparison"] for f in doc["findings"]}
    assert by_check == {"a": "resolved", "b": "not_rechecked"}
    assert doc["state"] == "partial" and doc["summary"]["findings"] == 0
    # Terceiro: "y" volta com B coletado → recorrente (não reverificado continua contando como presente).
    monkeypatch.setattr(collectors, "plan", fake_plan({"b": [finding("y")]}))
    third = runner.submit("compare-run-03", "manual")["run_id"]
    runner.execute(third)
    doc = json.loads((config.runs_root / third / "report.json").read_text(encoding="utf-8"))
    assert [f["comparison"] for f in doc["findings"]] == ["recurring"]


def test_real_collectors_produce_escaped_report(runner, monkeypatch, config):
    hostile = finding("h", summary="<script>alert(1)</script>")
    real = collectors.plan("startup-light")
    monkeypatch.setattr(collectors, "plan", lambda _p, _f=True: real + [
        PlannedCheck("evil", "Hostil", lambda _c, check: check.findings.append(hostile), "light")])
    run_id = runner.submit("real-collectors-1", "manual")["run_id"]
    runner.execute(run_id)
    run = runner.store.run(run_id)
    checks = {c["id"]: c["status"] for c in run["checks"]}
    assert checks["vcs"] == "error"  # git configurado não existe: erro de coleta
    assert checks["services"] == "collected"  # RAG desligado foi observado: vira achado, não erro
    assert run["state"] == "partial"
    html = (config.runs_root / run_id / "report.html").read_text(encoding="utf-8")
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert {a["kind"] for a in run["artifacts"]} == {"json", "html"}
    doc = json.loads((config.runs_root / run_id / "report.json").read_text(encoding="utf-8"))
    assert doc["executed"] is True and doc["schema_version"] == 1 and doc["auto_fix"] is False
    assert doc["revision"]["source_state"] == "working_tree"
    assert any(f["rule"] == "rag.unavailable" for f in doc["findings"])


def test_full_audit_without_config_is_explicitly_not_executed(runner, config):
    runner.settings.save({"on_startup": True, "profile": "full-audit", "sync_to_server": False,
                          "investigate_with_ai": False, "workflow_url": ""}, 0)
    run_id = runner.submit("full-profile-01", "manual")["run_id"]
    runner.execute(run_id)
    checks = {c["id"]: c["status"] for c in runner.store.run(run_id)["checks"]}
    assert checks["editmode"] == "skipped" and checks["isolated_compile"] == "skipped"
    assert runner.store.run(run_id)["state"] == "partial"
