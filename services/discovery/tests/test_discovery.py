from __future__ import annotations

import os
import time

import pytest
from conftest import fake_fetch
from unity_rag.embeddings import HashEmbedder

from rag_discovery.catalogs import load_catalog, load_entries
from rag_discovery.code_scan import CodeProfile, scan_project, scan_source
from rag_discovery.config import ConfigError, load_config
from rag_discovery.llm import build_prompt, parse_topics
from rag_discovery.planner import api_candidates, source_id_of, topic_candidates
from rag_discovery.runner import Deps, build_plan, submit
from rag_discovery.state import Store


def by_url(entries):
    return {e.url: e for e in entries}


def test_parsers_read_each_index_format(config):
    entries, warnings = load_entries(config, fetch=fake_fetch)
    assert warnings == []
    urls = by_url(entries)
    tilemap = urls["https://docs.example/ScriptReference/Tilemaps.Tilemap.html"]
    assert tilemap.symbol == "Tilemap" and "UnityEngine.Tilemaps" in tilemap.namespaces
    assert urls["https://docs.example/ScriptReference/Transform-position.html"].symbol == "Transform.position"
    manual = urls["https://docs.example/Manual/tilemaps-intro.html"]
    assert manual.topic and manual.label == "Unity Manual > Introduction to tilemaps"
    button = urls["https://docs.example/Packages/ugui/api/UnityEngine.UI.Button.html"]
    assert button.namespaces == frozenset({"UnityEngine.UI"})
    assert not any("#" in e.url for e in entries)  # membros com âncora ficam de fora
    face = [e for e in entries if e.catalog == "facepunch"]
    assert [e.title for e in face] == ["SteamMatchmaking", "Lobby", "SteamPort", "P2P Networking"]
    face = {e.title: e for e in face}
    assert face["SteamMatchmaking"].api and not face["SteamMatchmaking"].topic
    assert face["Lobby"].symbol == "Lobby" and face["Lobby"].namespaces == frozenset({"Steamworks.Data"})
    assert not face["SteamPort"].topic  # membro: nunca vira resultado de tópico
    guide = face["P2P Networking"]
    assert not guide.api and guide.topic and guide.symbol is None


def test_stale_cache_is_used_when_fetch_fails(config):
    spec = config.catalogs[0]
    load_catalog(config, spec, fetch=fake_fetch)
    path = next((config.cache_root / "catalogs").glob("unity-scripting-*.txt"))
    old = time.time() - 30 * 86400
    os.utime(path, (old, old))

    def offline(url, ua):
        raise OSError("sem rede")

    entries, warning = load_catalog(config, spec, fetch=offline)
    assert entries and "cache antigo" in warning


def test_code_scan_ignores_comments_and_strings(workspace, config):
    from unity_rag.config import load_config as load_rag

    rag = load_rag(config.rag_config)
    profile = scan_project(rag.scripts_root, rag.unity_project_root)
    assert profile.files == 2
    assert "Rigidbody" not in profile.types
    assert profile.types["Grid"] == 2 and profile.types["MonoBehaviour"] == 2
    assert profile.members["Physics2D.Raycast"] == 1
    assert {"Board", "Hud"} <= profile.declared
    assert profile.packages == ["com.unity.ugui 2.0.0"] and profile.unity_version == "6000.3.10f1"


def test_api_candidates_respect_namespaces_and_known(config):
    entries, _ = load_entries(config, fetch=fake_fetch)
    profile = CodeProfile()
    scan_source("using UnityEngine; using UnityEngine.UI; using Steamworks;\n"
                "class A : MonoBehaviour { Button b; Grid g; void F(){ SteamMatchmaking.X(); } }", profile)
    scan_source("using UnityEngine;\nclass Grid {} class B : MonoBehaviour { Grid g; }", profile)
    scan_source("using UnityEngine.UIElements;\nclass C { VisualElement v; }", profile)
    found = {c.url: c for c in api_candidates(entries, profile, set(), limit=50)}
    assert "https://docs.example/Packages/ugui/api/UnityEngine.UI.Button.html" in found
    # UIElements é importado, mas não no arquivo que usa Button.
    assert "https://docs.example/ScriptReference/UIElements.Button.html" not in found
    assert "https://docs.example/ScriptReference/Grid.html" not in found  # projeto declara Grid
    assert "https://wiki.example/steamworks/SteamMatchmaking" in found
    mono = found["https://docs.example/ScriptReference/MonoBehaviour.html"]
    assert mono.score == 2 and mono.reason == "MonoBehaviour usado em 2 script(s) (UnityEngine)"
    known = {mono.source_id}
    again = api_candidates(entries, profile, known, limit=50)
    assert mono.url not in {c.url for c in again}
    assert len(api_candidates(entries, profile, set(), limit=50, min_files=2)) == 1


def test_topic_candidates_rank_by_similarity(config, tmp_path):
    entries, _ = load_entries(config, fetch=fake_fetch)
    embedder = HashEmbedder()
    found = topic_candidates(entries, [("introduction to tilemaps", "teste")], embedder, set(), limit=5,
                             min_score=0.3, per_topic=1, cache_dir=tmp_path / "emb")
    assert [c.url for c in found] == ["https://docs.example/Manual/tilemaps-intro.html"]
    assert "teste" in found[0].reason
    calls = embedder.calls
    topic_candidates(entries, [("audio overview", "x")], embedder, set(), limit=5, min_score=0.3, per_topic=1,
                     cache_dir=tmp_path / "emb")
    assert embedder.calls == calls + 1  # títulos vêm do cache; só o tópico é codificado


def test_parse_topics_cleans_model_output():
    text = ("Here are topics:\n1. Tilemap rule tiles\n- Netcode for GameObjects RPCs.\n* **Steam lobby data**\n"
            "Tilemap rule tiles\nWhy?\n\nOk")
    assert parse_topics(text, 5) == ["Here are topics", "Tilemap rule tiles", "Netcode for GameObjects RPCs",
                                     "Steam lobby data"]
    assert len(parse_topics(text, 2)) == 2


def test_prompt_mentions_project_facts():
    profile = CodeProfile(files=3, packages=["com.unity.ugui 2.0.0"], unity_version="6000.3.10f1")
    scan_source("using UnityEngine.UI; class DiceRoller {} class X { DiceRoller d; }", profile)
    prompt = build_prompt("dicevtt", profile, ["Unity Grid"], ["como rolar dados?"], 4)
    assert "6000.3.10f1" in prompt and "DiceRoller" in prompt and "Unity Grid" in prompt
    assert "como rolar dados?" in prompt and "List 4" in prompt


def test_config_rejects_bad_catalog(tmp_path):
    path = tmp_path / "d.toml"
    path.write_text('[[catalogs]]\nid="x"\nkind="rss"\nindex="https://a"\nbase="https://a"\napi=true\n')
    with pytest.raises(ConfigError):
        load_config(path)


def _deps(topics):
    def generator(rag, prompt, count, max_new_tokens, on_token=None):
        assert "Project: dicevtt" in prompt
        return topics

    return Deps(fetch=fake_fetch, embedder_factory=lambda _rag: HashEmbedder(), topic_generator=generator)


def test_plan_combines_code_and_topics_without_duplicates(config):
    store = Store(config.state_path)
    plan = build_plan(config, store, use_llm=True, log=lambda _m: None, deps=_deps(["netcode gameobjects overview"]))
    strategies = {c.url: c.strategy for c in plan.candidates}
    assert strategies["https://docs.example/ScriptReference/Tilemaps.Tilemap.html"] == "code_api"
    assert strategies["https://docs.example/Manual/tilemaps-intro.html"] == "topic"  # lista fixa
    assert strategies["https://docs.example/Manual/multiplayer-netcode.html"] == "topic"  # AirLLM
    assert ("netcode gameobjects overview", "AirLLM") in plan.topics
    assert len({c.source_id for c in plan.candidates}) == len(plan.candidates)
    store.close()


def test_run_submits_marks_results_and_indexes(config, monkeypatch):
    from rag_discovery import runner

    store = Store(config.state_path)
    plan = build_plan(config, store, use_llm=False, log=lambda _m: None, deps=_deps([]))
    store.propose(plan.run_id, plan.candidates)
    urls = [c.url for c in plan.candidates]
    calls = []

    def fake_call(self, method, path, body=None, timeout=30):
        calls.append((self.name, method, path))
        if path == "/v1/ingestion/batches":
            assert body["urls"].splitlines() == urls and body["mode"] == "online"
            return {"id": "b1"}
        if path.startswith("/v1/ingestion/batches/b1"):
            items = [{"raw_url": u, "status": "completed" if i else "failed",
                      "result": None if i else {"reason_code": "not_found"}} for i, u in enumerate(urls)]
            return {"state": "completed_with_errors", "total": len(urls), "counts": {}, "items": items}
        if path == "/v1/rag/index-jobs":
            assert body == {"scope": "documents"}
            return {"job_id": "j1"}
        return {"state": "completed"}

    monkeypatch.setattr(runner.LocalService, "call", fake_call)
    totals = submit(config, store, plan, log=lambda _m: None, sleep=lambda _s: None)
    assert totals == {"failed": 1, "ingested": len(urls) - 1}
    assert ("RAG", "POST", "/v1/rag/index-jobs") in calls
    failed = store.candidates("failed")
    assert failed[0]["url"] == urls[0] and failed[0]["detail"] == "not_found"
    # Na próxima rodada nada disso volta a ser proposto.
    again = build_plan(config, store, use_llm=False, log=lambda _m: None, deps=_deps([]))
    assert not {c.url for c in again.candidates} & set(urls)
    assert store.reject(urls[0]) == 1
    store.close()


def test_source_id_matches_ingestion_canonical_form():
    assert source_id_of("https://Docs.Example/ScriptReference/Grid.html#x") == source_id_of(
        "https://docs.example/ScriptReference/Grid.html")
    assert source_id_of("http://localhost/x") is None


def test_import_local_corpus_converts_srd_xml_and_markdown_idempotently(config, tmp_path):
    from rag_discovery.local_corpus import import_local_corpus

    vault = tmp_path / "vault"
    srd = vault / "Projeto VTT RPG" / "DadosVariaveisSistema" / "sistemas" / "quinta-edicao-srd" / "magias"
    srd.mkdir(parents=True)
    (srd / "fireball.xml").write_text(
        "<?xml version='1.0' encoding='utf-8'?>\n"
        "<spell id='fireball' source='SRD'><name>Bola de Fogo</name>"
        "<summary>Uma explosão flamejante detona em um ponto à sua escolha dentro do alcance.</summary>"
        "<metadata><level>3</level><school>Evocação</school></metadata></spell>",
        encoding="utf-8",
    )
    info = vault / "informacoes"
    info.mkdir(parents=True)
    (info / "regras_combate.md").write_text(
        "# Regras de Combate\n\nOrdem de iniciativa, ações por turno, reação e movimento em grid tático.",
        encoding="utf-8",
    )

    first = import_local_corpus(config, vault_root=vault, index=False, log=lambda _m: None)
    assert first == {"added": 2, "skipped": 0, "total": 2}
    second = import_local_corpus(config, vault_root=vault, index=False, log=lambda _m: None)
    assert second == {"added": 0, "skipped": 2, "total": 2}

