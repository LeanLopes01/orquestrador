from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_ingestion.config import load_config  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
WORKSPACE = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    """Nenhum teste da ingestão abre conexão fora do loopback."""
    real = socket.socket.connect

    def guarded(self, address):
        host = address[0] if isinstance(address, tuple) else address
        if host not in {"127.0.0.1", "::1", "localhost"}:
            raise AssertionError(f"conexão externa bloqueada no teste: {address}")
        return real(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded)
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))])


@pytest.fixture
def config(tmp_path):
    path = tmp_path / ".local" / "ingestion.toml"
    path.parent.mkdir()
    path.write_text(
        'project_id = "dicevtt"\noutput_root = "../documentacao_rag"\nstate_path = "ingestion/state.sqlite3"\n'
        'cache_root = "ingestion/cache"\nmanifests_root = "ingestion/manifests"\nlog_path = "ingestion/logs/events.jsonl"\n'
        'token_path = "ingestion/api-token"\n[network]\nmax_attempts = 3\nbackoff_seconds = [0.01, 0.01]\n'
        'retry_budget_seconds = 5\ndomain_pause_seconds = 0\n[extraction]\nmin_chars = 120\n',
        encoding="utf-8",
    )
    return load_config(path)
