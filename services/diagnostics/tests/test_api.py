from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from dicevtt_diagnostics import collectors
from dicevtt_diagnostics.api import create_app
from dicevtt_diagnostics.collectors import PlannedCheck


@pytest.fixture()
def client(config, monkeypatch):
    monkeypatch.setattr(collectors, "plan", lambda _p, _f=True: [PlannedCheck("a", "Check A", lambda _c, _check: None, "light")])
    app = create_app(config)
    token = config.token_path.read_text(encoding="ascii").strip()
    with TestClient(app, base_url="http://127.0.0.1:8768", client=("127.0.0.1", 50000)) as http:
        http.headers["X-Local-Token"] = token
        yield http


def wait_finished(client, run_id):
    for _ in range(100):
        run = client.get(f"/v1/audits/{run_id}").json()
        if run["state"] not in ("queued", "collecting"):
            return run
        time.sleep(0.05)
    raise AssertionError("auditoria não terminou")


def test_requires_token_loopback_host_and_no_origin(client):
    assert client.get("/v1/diagnostics/health", headers={"X-Local-Token": "x"}).status_code == 401
    assert client.get("/v1/diagnostics/health", headers={"Origin": "http://evil"}).status_code == 403
    assert client.get("/v1/diagnostics/health", headers={"Host": "evil:8768"}).status_code == 403
    health = client.get("/v1/diagnostics/health").json()
    assert health["service"] == "dicevtt-diagnostics"
    assert health["capabilities"] == {"profiles": ["startup-light"], "full_audit": False, "sync": False,
                                      "ai_investigation": True, "auto_fix": False}  # conftest não tem [full]


def test_audit_flow_idempotency_and_report(client, config):
    assert client.post("/v1/audits", json={}).status_code == 400  # sem Idempotency-Key
    bad = client.post("/v1/audits", json={"auto_fix": True}, headers={"Idempotency-Key": "manual-0001"})
    assert bad.status_code == 400
    created = client.post("/v1/audits", json={"trigger": "manual"}, headers={"Idempotency-Key": "manual-0002"})
    assert created.status_code == 202
    run_id = created.json()["run_id"]
    repeat = client.post("/v1/audits", json={"trigger": "manual"}, headers={"Idempotency-Key": "manual-0002"})
    assert repeat.status_code == 200 and repeat.json()["duplicate"] and repeat.json()["run_id"] == run_id
    run = wait_finished(client, run_id)
    assert run["state"] == "completed" and run["report"]["run_id"] == run_id
    html = client.get(f"/v1/audits/{run_id}/report", params={"format": "html"})
    assert html.headers["content-type"].startswith("text/html")
    assert "sandbox" in html.headers["content-security-policy"]
    listing = client.get("/v1/audits", params={"limit": 1}).json()
    assert [r["id"] for r in listing["items"]] == [run_id]
    assert client.get("/v1/audits/../../etc").status_code == 404
    (config.runs_root / run_id / "report.html").write_text("adulterado", encoding="utf-8")
    assert client.get(f"/v1/audits/{run_id}/report", params={"format": "html"}).status_code == 409


def test_settings_revision_and_validation(client):
    current = client.get("/v1/settings").json()
    assert current["revision"] == 0 and current["on_startup"] is True
    body = {"settings": {**{k: current[k] for k in ("on_startup", "profile", "sync_to_server",
                                                      "investigate_with_ai", "workflow_url")}, "on_startup": False},
            "expected_revision": 0}
    saved = client.put("/v1/settings", json=body)
    assert saved.status_code == 200 and saved.json()["revision"] == 1
    assert client.put("/v1/settings", json=body).status_code == 409  # revisão velha
    evil = {**body, "expected_revision": 1,
            "settings": {**body["settings"], "workflow_url": "https://x.com/workflow/1?token=segredo"}}
    assert client.put("/v1/settings", json=evil).status_code == 400
    disabled = client.post("/v1/audits", json={"trigger": "startup"}, headers={"Idempotency-Key": "startup-0001"})
    assert disabled.status_code == 200 and disabled.json()["outcome"] == "disabled"
    assert client.get("/v1/diagnostics/health").json()["last_startup"]["outcome"] == "disabled"
