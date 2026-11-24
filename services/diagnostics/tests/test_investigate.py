from __future__ import annotations

import json
import threading
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from dicevtt_diagnostics import collectors, investigate
from dicevtt_diagnostics.collectors import PlannedCheck
from dicevtt_diagnostics.collectors.base import Finding
from dicevtt_diagnostics.config import AiConfig, RagLink
from dicevtt_diagnostics.investigate import Investigator, validate_claude
from dicevtt_diagnostics.jobs import Runner
from dicevtt_diagnostics.settings import SettingsError, SettingsStore
from dicevtt_diagnostics.store import AuditStore

BASE_SETTINGS = {"on_startup": True, "profile": "startup-light", "sync_to_server": False, "workflow_url": ""}


class FakeRag:
    """RAG local falso: health + asks. `answer` decide o que o 'modelo' responde."""

    def __init__(self, answer: str = "A causa provável está em [S1].", model_state: str = "unloaded",
                 never_finish: bool = False) -> None:
        self.answer, self.model_state, self.never_finish = answer, model_state, never_finish
        self.queries: list[str] = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def _send(self, data):
                body = json.dumps(data).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if self.path == "/v1/rag/health":
                    return self._send({"online": True, "starting": False,
                                       "model": {"state": fake.model_state, "name": "Qwen-teste", "reason": None}})
                state = "running" if fake.never_finish else "completed"
                return self._send({"id": "a1", "state": state, "result": {
                    "answer": fake.answer, "generated_tokens": 12,
                    "sources": [{"id": "S1", "relpath": "Assets/Scripts/A.cs", "kind": "code_pointer", "hash": "h",
                                 "lines": [1, 9]}]}})

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or b"{}")
                if self.path == "/v1/rag/asks":
                    fake.queries.append(body["query"])
                return self._send({"ask_id": "a1", "state": "queued"})

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    @property
    def port(self) -> int:
        return self.server.server_address[1]


@pytest.fixture()
def finished_run(config, monkeypatch, tmp_path):
    """Uma auditoria concluída com duas ocorrências, pronta para investigar."""
    token = tmp_path / "rag-token"
    token.write_text("t" * 40)
    findings = [Finding(rule="unity.compile-error", severity="high", state="confirmed", key="x",
                        summary="Erro CS1002 em A.cs", file="Assets/Scripts/A.cs", line=3),
                Finding(rule="rag.unavailable", severity="info", state="confirmed", key="y", summary="RAG desligado")]
    monkeypatch.setattr(collectors, "plan", lambda _p, _f=True: [
        PlannedCheck("a", "A", lambda _c, check: check.findings.extend(findings), "light")])
    store = AuditStore(config.state_path)
    settings = SettingsStore(config.settings_path)
    runner = Runner(config, store, settings)
    run_id = runner.submit("investigate-0001", "manual")["run_id"]
    runner.execute(run_id)
    yield config, store, settings, run_id, token
    store.close()


def make(config, store, settings, token, rag: FakeRag | None, **ai):
    cfg = replace(config, rag=RagLink(rag.port if rag else 9, token, config.project_root),
                  ai=replace(AiConfig(), **ai))
    return Investigator(cfg, store, settings)


def test_local_hypothesis_needs_a_real_citation(finished_run):
    config, store, settings, run_id, token = finished_run
    rag = FakeRag()
    investigator = make(config, store, settings, token, rag)
    store.request_investigation(run_id, "manual")
    investigator.run(run_id)
    row = store.investigation(run_id)
    result = json.loads((config.runs_root / run_id / "investigation.json").read_text(encoding="utf-8"))
    assert row["state"] == "completed" and row["provider"] == "local-rag" and row["model"] == "Qwen-teste"
    assert result["prompt_version"] == investigate.PROMPT_VERSION and result["data_left_pc"] is False
    assert [i["fingerprint"] for i in result["items"]] == [Finding("unity.compile-error", "", "", "", "x").fingerprint]
    item = result["items"][0]  # info não é investigada
    assert item["status"] == "supported" and item["sources"][0]["path"] == "Assets/Scripts/A.cs"
    assert "Erro CS1002" in rag.queries[0]
    report = json.loads((config.runs_root / run_id / "report.json").read_text(encoding="utf-8"))
    assert all("hypothesis" not in f for f in report["findings"])  # o relatório dos coletores não muda
    rag.server.shutdown()


def test_answer_without_citation_is_unsupported(finished_run):
    config, store, settings, run_id, token = finished_run
    rag = FakeRag(answer="Provavelmente um ponto e vírgula.")
    store.request_investigation(run_id, "manual")
    make(config, store, settings, token, rag).run(run_id)
    result = json.loads((config.runs_root / run_id / "investigation.json").read_text(encoding="utf-8"))
    assert result["items"][0]["status"] == "unsupported"
    rag.server.shutdown()


@pytest.mark.parametrize("model_state", ["not_configured", None])
def test_model_or_rag_unavailable_skips_without_touching_report(finished_run, model_state):
    config, store, settings, run_id, token = finished_run
    rag = FakeRag(model_state=model_state) if model_state else None
    store.request_investigation(run_id, "manual")
    make(config, store, settings, token, rag).run(run_id)
    row = store.investigation(run_id)
    assert row["state"] == "skipped" and row["error"]
    assert store.run(run_id)["state"] in ("completed", "partial")
    if rag:
        rag.server.shutdown()


def test_timeout_is_explicit(finished_run, monkeypatch):
    config, store, settings, run_id, token = finished_run
    rag = FakeRag(never_finish=True)
    monkeypatch.setattr(investigate.time, "sleep", lambda _s: None)
    store.request_investigation(run_id, "manual")
    make(config, store, settings, token, rag, local_timeout_seconds=0.2, total_timeout_seconds=60).run(run_id)
    result = json.loads((config.runs_root / run_id / "investigation.json").read_text(encoding="utf-8"))
    assert result["items"][0]["status"] == "timeout" and result["state"] == "failed"
    rag.server.shutdown()


def test_tampered_report_is_not_investigated(finished_run):
    config, store, settings, run_id, token = finished_run
    (config.runs_root / run_id / "report.json").write_text("{}", encoding="utf-8")
    store.request_investigation(run_id, "manual")
    make(config, store, settings, token, FakeRag()).run(run_id)
    assert store.investigation(run_id)["state"] == "failed"


def test_auto_request_only_with_preference_and_retry_after_failure(finished_run):
    config, store, settings, run_id, token = finished_run
    investigator = make(config, store, settings, token, None)
    investigator.after_audit(run_id, "partial")
    assert store.investigation(run_id) is None  # preferência desligada
    settings.save({**BASE_SETTINGS, "investigate_with_ai": True}, 0)
    investigator.after_audit(run_id, "partial")
    assert store.investigation(run_id)["state"] == "queued"
    assert store.request_investigation(run_id, "manual")["created"] is False  # já na fila
    store.update_investigation(run_id, state="skipped")
    again = store.request_investigation(run_id, "manual")
    assert again["created"] and again["attempt"] == 2


def test_claude_requires_consent_and_validates_sources(project, tmp_path):
    with pytest.raises(SettingsError):
        SettingsStore(tmp_path / "s.json").save({**BASE_SETTINGS, "investigate_with_ai": True,
                                                 "ai_provider": "claude-code"}, 0)
    with pytest.raises(investigate.Skip):
        investigate.claude_available(type("C", (), {"ai": AiConfig()})(), allowed=False)
    ok = validate_claude({"hypothesis": "h", "confidence": "high", "sources": [
        {"path": "Assets/Scripts/A.cs", "lines": [1, 2]}, {"path": "../../Windows/win.ini"}]}, project)
    assert ok["status"] == "supported" and [s["valid"] for s in ok["sources"]] == [True, False]
    assert validate_claude({"hypothesis": "h", "sources": [{"path": "nao/existe.cs"}]}, project)["status"] == "unsupported"
    assert validate_claude(None, project)["status"] == "failed"


def test_selection_prefers_variety_over_repeats():
    def f(rule, summary, severity="high", file=None):
        return {"rule": rule, "summary": summary, "severity": severity, "file": file, "comparison": "new"}
    doc = {"findings": [f("validator.failure", "Guildas: a"), f("validator.failure", "Guildas: b"),
                        f("validator.failure", "Guildas: c"), f("validator.failure", "Salas: x"),
                        f("assets.missing-script", "s", file="Assets/Scenes/Desktop.unity"),
                        f("rag.unavailable", "r", severity="info")]}
    picked = [x["summary"] for x in investigate.select_findings(doc, 3)]
    assert picked == ["Guildas: a", "Salas: x", "s"]
    assert len(investigate.select_findings(doc, 10)) == 5  # info fica de fora; repetições completam as vagas
