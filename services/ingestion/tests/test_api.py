import time

import pytest
from fastapi.testclient import TestClient
from test_pipeline import ARTICLE, FakeWeb, transcript

from rag_ingestion.api import create_app
from rag_ingestion.events import EventLog
from rag_ingestion.pipeline import Pipeline
from rag_ingestion.repository import Repository


@pytest.fixture
def client(config):
    repo = Repository(config.state_path)
    web = FakeWeb({"https://ok.example/doc": [ARTICLE]})
    pipeline = Pipeline(config, repo, EventLog(config.log_path), fetch_page=web, fetch_transcript=transcript,
                        sleep=lambda s: None)
    app = create_app(config, pipeline=pipeline)
    token = config.token_path.read_text(encoding="ascii").strip()
    with TestClient(app, base_url=f"http://127.0.0.1:{config.port}", client=("127.0.0.1", 50000)) as http:
        http.headers["X-Local-Token"] = token
        yield http


def test_batch_lifecycle_and_idempotent_request_id(client):
    manifest = {"schema_version": 1, "sources": [{"original_url": "https://ok.example/doc"}]}
    created = client.post("/v1/ingestion/batches", json={"request_id": "r1", "project_id": "dicevtt",
                                                          "mode": "online", "manifest": manifest})
    assert created.status_code == 202
    batch_id = created.json()["id"]
    same = client.post("/v1/ingestion/batches", json={"request_id": "r1", "project_id": "dicevtt",
                                                       "mode": "online", "manifest": manifest})
    assert same.json()["id"] == batch_id
    conflict = client.post("/v1/ingestion/batches", json={"request_id": "r1", "mode": "offline", "manifest": manifest})
    assert conflict.status_code == 409
    for _ in range(100):
        batch = client.get(f"/v1/ingestion/batches/{batch_id}").json()
        if batch["state"] not in {"queued", "running"}:
            break
        time.sleep(0.05)
    assert batch["state"] == "completed" and batch["counts"]["completed"] == 1
    documents = client.get("/v1/ingestion/documents").json()["documents"]
    assert len(documents) == 1
    detail = client.get(f"/v1/ingestion/documents/{documents[0]['source_id']}").json()
    assert detail["markdown"].startswith("Fonte: https://ok.example/doc")
    assert client.get("/v1/ingestion/batches").json()["batches"][0]["id"] == batch_id


def test_rejects_other_projects_bad_input_and_foreign_callers(client):
    assert client.post("/v1/ingestion/batches", json={"project_id": "outro", "urls": "https://a.com"}).status_code == 400
    assert client.post("/v1/ingestion/batches", json={"mode": "x", "urls": "https://a.com"}).status_code == 400
    assert client.get("/v1/ingestion/health", headers={"X-Local-Token": "x"}).status_code == 401
    assert client.get("/v1/ingestion/health", headers={"Origin": "http://evil"}).status_code == 403
    health = client.get("/v1/ingestion/health").json()
    assert health["service"] == "rag-ingestion" and health["writable"]["output"] is True
