"""Regression: long task results used to make conversation GET return HTTP 500."""

import json
from unittest.mock import AsyncMock

import pytest

from src.jarvis_control.desktop import DesktopHub
from src.jarvis_control.orchestrator import Orchestrator
from src.jarvis_control.store import Store


@pytest.fixture
def saved(monkeypatch):
    store = Store(":memory:")
    hub = DesktopHub(store)
    orch = Orchestrator(":memory:", store, hub, hub.bus)
    # Reading and persisting evidence must not start real agents in these tests.
    monkeypatch.setattr(orch, "_spawn", lambda coro: coro.close())
    db = orch._db
    db.execute(
        "INSERT INTO conversations (id,project,device_id,title,state,created_at,updated_at) VALUES ('c','dicevtt','d','Test','running',1,1)"
    )
    db.execute(
        "INSERT INTO runs (id,conversation_id,plan_id,state,host,created_at,updated_at) VALUES ('r','c','p','running','computer',1,1)"
    )
    db.execute(
        "INSERT INTO tasks (id,run_id,idx,key,agent,title,body,state,job_id) VALUES ('t','r',0,'impl','claude','Test','{}','running','j')"
    )
    db.execute(
        "INSERT INTO jobs (id,purpose,conversation_id,run_id,task_id,state,params,created_at) VALUES ('j','task','c','r','t','running','{"
        + '"agent":"claude"'
        + "}',1)"
    )
    yield orch
    db.close()


async def test_large_result_survives_job_processing_and_conversation_read(saved):
    result = {
        "ok": True,
        "text": 'ação "linha"\n\\' * 45_000,
        "changes": {"modified": ["A.cs"]},
    }
    assert len(json.dumps(result, ensure_ascii=False)) > 400_000
    saved.record_job_update({"id": "j", "state": "completed", "result": result})
    assert (
        json.loads(saved._row("SELECT result FROM jobs WHERE id='j'")["result"])
        == result
    )
    await saved._process("j")
    task = saved.conversation("c")["runs"][0]["tasks"][0]
    assert task["result"] == result
    assert task["state"] == "completed"


def test_legacy_truncated_task_recovers_exact_job_without_mutation(saved):
    result = {"ok": True, "text": "á" * 210_000, "changes": {"added": ["A.cs"]}}
    raw = json.dumps(result, ensure_ascii=False)
    saved._db.execute("UPDATE tasks SET result = ?", (raw[:200_000],))
    saved._db.execute("UPDATE jobs SET result = ?", (raw,))
    before = saved._db.total_changes
    assert saved.conversation("c")["runs"][0]["tasks"][0]["result"] == result
    assert saved._db.total_changes == before
    assert (
        saved._row("SELECT result FROM tasks WHERE id='t'")["result"] == raw[:200_000]
    )


@pytest.mark.parametrize("job_raw", [None, '{"ok": true, "text": "cut', "[]"])
def test_unrecoverable_result_keeps_conversation_readable(saved, job_raw):
    saved._db.execute("UPDATE tasks SET result = ?", ('{"text": "cut',))
    saved._db.execute("UPDATE jobs SET result = ?", (job_raw,))
    task = saved.conversation("c")["runs"][0]["tasks"][0]
    assert task["result"]["ok"] is False
    assert task["result"]["error"] == "invalid_stored_result"
    assert task["state"] == "running"


def test_does_not_recover_from_unrelated_job(saved):
    saved._db.execute("UPDATE tasks SET result = ?", ('{"text": "cut',))
    saved._db.execute("UPDATE jobs SET task_id='another-task', result='{}'")
    assert saved.run("r")["tasks"][0]["result"]["error"] == "invalid_stored_result"


async def test_corrupt_legacy_job_is_processed_as_failure(saved, monkeypatch):
    saved._db.execute(
        "UPDATE jobs SET state='completed', result = ?", ('{"text": "cut',)
    )
    handler = AsyncMock()
    monkeypatch.setattr(saved, "_task_result", handler)
    await saved._process("j")
    assert handler.call_args.args[1] == "failed"
    assert handler.call_args.args[2]["error"] == "invalid_stored_result"


def test_empty_result_stays_absent(saved):
    assert saved.run("r")["tasks"][0]["result"] is None
