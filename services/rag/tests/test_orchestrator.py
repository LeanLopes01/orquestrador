import threading
import time

import pytest
from conftest import copy_fixture, wait_for

from unity_rag.airllm_engine import AirLlmEngine, GenerationCancelled
from unity_rag.config import GeneratorConfig
from unity_rag.orchestrator import CapabilityUnavailable


def test_ask_returns_answer_sources_and_progress(make_rag):
    rag = make_rag()
    copy_fixture("NetworkManager.cs", rag.config.scripts_root / "NetworkManager.cs")
    rag.submit_index("code").result()
    events = []
    answer = rag.ask("Como funcionam os lobbies Steamworks?", events.append)
    assert answer.answer.startswith("Resposta de teste")
    assert answer.sources[0]["included"] is True
    stages = [e.stage for e in events]
    assert stages[0] == "embeddings" and "generating" in stages and stages[-1] == "done"
    assert answer.model == "test/fake-generator" and answer.timings_ms["total"] >= 0


def test_generations_are_serialized_and_retrieve_stays_available(make_rag):
    rag = make_rag(delay=0.6)
    copy_fixture("SemComentario.cs", rag.config.scripts_root / "SemComentario.cs")
    rag.submit_index("code").result()
    futures = [rag.ask_async("pergunta um"), rag.ask_async("pergunta dois")]
    started = time.monotonic()
    while not futures[0].running():
        time.sleep(0.01)
    rag.retrieve("SemComentario")  # busca não espera o gerador
    assert time.monotonic() - started < 0.5
    for future in futures:
        future.result(timeout=10)
    assert rag._generator.max_concurrent == 1


def test_cancel_stops_without_parallel_generation(make_rag):
    rag = make_rag(delay=5)
    cancel = threading.Event()
    future = rag.ask_async("demorada", cancel=cancel)
    assert wait_for(lambda: rag._generator.concurrent == 1)
    queued = rag.ask_async("seguinte")
    cancel.set()
    with pytest.raises(GenerationCancelled):
        future.result(timeout=5)
    queued_result = None
    rag._generator.delay = 0
    queued_result = queued.result(timeout=10)
    assert queued_result.answer and rag._generator.max_concurrent == 1


def test_missing_generator_keeps_search_available(make_rag, tmp_path):
    rag = make_rag()
    rag._generator = AirLlmEngine(GeneratorConfig(enabled=True, model_path=tmp_path / "sem-pesos", repo_id="x"))
    with pytest.raises(CapabilityUnavailable) as exc:
        rag.ask("pergunta")
    assert exc.value.code == "model_assets_missing"
    assert rag.retrieve("pergunta").sources == []
    assert rag.health()["model"]["state"] == "error"


def test_health_does_not_load_the_model(make_rag):
    rag = make_rag()
    health = rag.health()
    assert health["model"]["state"] == "unloaded"
    assert health["embeddings"]["state"] == "ready" and health["index"]["state"] == "ready"
