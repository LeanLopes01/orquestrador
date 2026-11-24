import time

import pytest
from conftest import WordTokenizer, copy_fixture, write_config
from fastapi.testclient import TestClient

from unity_rag.airllm_engine import FakeEngine
from unity_rag.api import create_app
from unity_rag.config import load_config
from unity_rag.embeddings import HashEmbedder
from unity_rag.orchestrator import RagOrchestrator


@pytest.fixture
def client(tmp_path):
    config = load_config(write_config(tmp_path))
    copy_fixture("NetworkManager.cs", config.scripts_root / "NetworkManager.cs")
    copy_fixture("regras-grid.md", config.docs_root / "regras-grid.md")
    rag = RagOrchestrator(config, embedder=HashEmbedder(), generator=FakeEngine(0.2, WordTokenizer()), watch=False)
    stopped = []
    app = create_app(config, orchestrator=rag, on_shutdown=lambda: stopped.append(True))
    token = config.token_path.read_text(encoding="ascii").strip()
    with TestClient(app, base_url=f"http://127.0.0.1:{config.port}", client=("127.0.0.1", 50000)) as http:
        http.headers["X-Local-Token"] = token
        for _ in range(100):
            if not http.get("/v1/rag/health").json()["starting"]:
                break
            time.sleep(0.05)
        yield http, stopped


def poll(http, path, done=("completed", "failed", "cancelled")):
    for _ in range(200):
        body = http.get(path).json()
        if body.get("state") in done:
            return body
        time.sleep(0.05)
    raise AssertionError(body)


def test_security_rejects_missing_token_foreign_host_and_browser_origin(client):
    http, _ = client
    assert http.get("/v1/rag/health", headers={"X-Local-Token": "errado"}).status_code == 401
    assert http.get("/v1/rag/health", headers={"Host": "evil.example:8767"}).status_code == 403
    assert http.get("/v1/rag/health", headers={"Origin": "http://127.0.0.1:1420"}).status_code == 403


def test_document_folder_is_configured_and_open_is_authenticated(client, monkeypatch):
    http, _ = client
    folder = http.get('/v1/rag/document-folder').json()
    assert '.pdf' in folder['formats'] and folder['mode'] == 'manual'
    assert http.post('/v1/rag/document-folder/open', json={}, headers={'X-Local-Token': 'bad'}).status_code == 401
    import os
    if os.name == 'nt':
        opened = []
        monkeypatch.setattr(os, 'startfile', opened.append)
        assert http.post('/v1/rag/document-folder/open', json={'path': 'C:/outside'}).status_code == 200
        assert opened == [folder['path']]


def test_index_job_retrieve_and_ask_flow(client):
    http, _ = client
    job = http.post("/v1/rag/index-jobs", json={"project_id": "dicevtt", "scope": "all"})
    assert job.status_code == 202
    report = poll(http, f"/v1/rag/index-jobs/{job.json()['job_id']}")["report"]
    assert report["code"]["added"] == 1 and report["documents"]["added"] == 1
    retrieved = http.post("/v1/rag/retrieve", json={"project_id": "dicevtt", "query": "lobbies Steamworks grid"})
    assert retrieved.status_code == 200 and retrieved.json()["sources"]
    assert http.post("/v1/rag/retrieve", json={"project_id": "outro", "query": "x"}).status_code == 400
    assert http.post("/v1/rag/retrieve", json={"query": ""}).status_code == 400

    ask = http.post("/v1/rag/asks", json={"project_id": "dicevtt", "query": "Como sincroniza?", "request_id": "req-1"})
    assert ask.status_code == 202
    again = http.post("/v1/rag/asks", json={"project_id": "dicevtt", "query": "Como sincroniza?", "request_id": "req-1"})
    assert again.json()["ask_id"] == ask.json()["ask_id"]  # polling/reenvio não duplica
    final = poll(http, f"/v1/rag/asks/{ask.json()['ask_id']}")
    assert final["state"] == "completed" and final["result"]["answer"]
    assert final["progress"]["stage"] == "done"


def test_shutdown_endpoint_triggers_clean_exit(client):
    http, stopped = client
    assert http.post("/v1/rag/shutdown", json={}).json() == {"stopping": True}
    time.sleep(0.4)
    assert stopped == [True]
