"""Opt-in com assets reais: SentenceTransformer real (RAG_REAL_CONFIG) e AirLLM real
(RAG_AIRLLM_SMOKE=1). Nunca baixa modelos; sem os arquivos locais o teste é pulado."""

import os
import time
from pathlib import Path

import pytest
from conftest import copy_fixture, write_config

from unity_rag.config import load_config

REAL = os.environ.get("RAG_REAL_CONFIG")


def _real():
    if not REAL:
        pytest.skip("defina RAG_REAL_CONFIG=.local/rag.toml para usar os modelos locais")
    return load_config(REAL)


@pytest.mark.integration
def test_real_embeddings_rank_the_expected_sources(tmp_path):
    real = _real()
    from unity_rag.embeddings import SentenceTransformerEmbedder
    from unity_rag.orchestrator import RagOrchestrator
    from unity_rag.airllm_engine import FakeEngine

    config = load_config(write_config(tmp_path))
    copy_fixture("NetworkManager.cs", config.scripts_root / "NetworkManager.cs")
    copy_fixture("SemComentario.cs", config.scripts_root / "SemComentario.cs")
    copy_fixture("regras-grid.md", config.docs_root / "regras-grid.md")
    rag = RagOrchestrator(config, embedder=SentenceTransformerEmbedder(real.embedding), generator=FakeEngine(), watch=False)
    rag.start()
    try:
        rag.submit_index("all").result()
        result = rag.retrieve("Como os lobbies da Steam são gerenciados?")
        assert result.sources[0].relpath.endswith("NetworkManager.cs")
        docs = [s for s in rag.retrieve("Quanto custa mover uma célula no grid?").sources if s.kind == "documentation"]
        assert docs and docs[0].section == "Movimento"
    finally:
        rag.close()


@pytest.mark.airllm
def test_airllm_real_generation_smoke():
    if os.environ.get("RAG_AIRLLM_SMOKE") != "1":
        pytest.skip("defina RAG_AIRLLM_SMOKE=1 (leva minutos no CPU)")
    real = _real()
    import threading

    from unity_rag.airllm_engine import AirLlmEngine

    engine = AirLlmEngine(real.generator)
    tokenizer = engine.tokenizer()
    prompt = tokenizer.render("Responda em português em uma frase.", "O que é um grid hexagonal?")
    started = time.monotonic()
    text, count = engine.generate(prompt, max_new_tokens=16, cancel=threading.Event())
    elapsed = time.monotonic() - started
    print(f"\nAirLLM {engine.model_name}: {count} tokens em {elapsed:.1f}s → {text!r}")
    assert count > 0 and text
    assert Path(engine.shards_dir or ".").exists()
