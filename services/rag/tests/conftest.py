"""Fixtures: diretórios e Chroma temporários, embeddings determinísticos e gerador falso.

Validam lógica, não qualidade semântica (ver test_integration_real.py)."""

from __future__ import annotations

import socket
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from unity_rag.airllm_engine import FakeEngine  # noqa: E402
from unity_rag.config import load_config  # noqa: E402
from unity_rag.embeddings import HashEmbedder  # noqa: E402
from unity_rag.orchestrator import RagOrchestrator  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


class WordTokenizer:
    name = "test/words"

    def count(self, text: str) -> int:
        return len(text.split())

    def render(self, system: str, user: str) -> str:
        return f"{system}\n\n{user}"


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch, request):
    """Testes rápidos falham se tentarem abrir conexão fora do loopback."""
    if request.node.get_closest_marker("integration") or request.node.get_closest_marker("airllm"):
        return
    real = socket.socket.connect

    def guarded(self, address):
        host = address[0] if isinstance(address, tuple) else address
        if host not in {"127.0.0.1", "::1", "localhost"}:
            raise AssertionError(f"conexão externa bloqueada no teste: {address}")
        return real(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded)


def write_config(tmp_path: Path, **overrides) -> Path:
    scripts = tmp_path / "Unity" / "Assets" / "Scripts"
    docs = tmp_path / "documentacao_rag"
    scripts.mkdir(parents=True, exist_ok=True)
    docs.mkdir(parents=True, exist_ok=True)
    values = {
        "max_new_tokens": 50, "max_seq_len": 4000, "debounce_ms": 100, "code_top_k": 4, "doc_top_k": 4,
    } | overrides
    text = f"""
project_id = "dicevtt"
unity_project_root = "{(tmp_path / 'Unity').as_posix()}"
scripts_root = "{scripts.as_posix()}"
docs_root = "documentacao_rag"
chroma_path = "state/chroma"
index_state_path = "state/index-state.sqlite3"
token_path = "state/api-token"
offline = true
[embedding]
repo_id = "test/hash"
local_dir = "models/none"
[retrieval]
code_top_k = {values['code_top_k']}
doc_top_k = {values['doc_top_k']}
candidate_cap = 12
[chunking]
chunk_tokens = 40
overlap_tokens = 8
[watcher]
enabled = true
debounce_ms = {values['debounce_ms']}
[generator]
enabled = false
max_seq_len = {values['max_seq_len']}
max_new_tokens = {values['max_new_tokens']}
"""
    path = tmp_path / "rag.toml"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def config(tmp_path):
    return load_config(write_config(tmp_path))


@pytest.fixture
def make_rag(tmp_path):
    created: list[RagOrchestrator] = []

    def factory(*, watch: bool = False, delay: float = 0.0, **overrides) -> RagOrchestrator:
        cfg = load_config(write_config(tmp_path, **overrides))
        rag = RagOrchestrator(cfg, embedder=HashEmbedder(), generator=FakeEngine(delay, WordTokenizer()), watch=watch)
        rag.start()
        created.append(rag)
        return rag

    yield factory
    for rag in created:
        rag.close()


def wait_for(predicate, timeout: float = 5.0, interval: float = 0.05) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


def copy_fixture(name: str, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((FIXTURES / name).read_bytes())
    return target
