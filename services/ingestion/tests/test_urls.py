import json

import pytest
from conftest import FIXTURES, WORKSPACE

from rag_ingestion.inputs import InputError, from_manifest, load_input, parse_catalog
from rag_ingestion.urls import UrlError, classify, source_id_for

CASES = json.loads((FIXTURES / "url_cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=[c["input"] for c in CASES])
def test_url_cases_match_the_ui_rules(case):
    if case.get("error"):
        with pytest.raises(UrlError):
            classify(case["input"])
        return
    spec = classify(case["input"])
    assert spec.kind == case["kind"]
    assert spec.canonical_url == case["canonical"]
    assert spec.original_url == case["input"]
    assert spec.source_id == source_id_for(case["canonical"])


def test_catalog_contract_19_sources_12_enabled():
    text = (WORKSPACE / "docs" / "catalogo-fontes-documentacao-rag.md").read_text(encoding="utf-8")
    data, enabled = parse_catalog(text)
    assert len(data["sources"]) == 19 and len(enabled) == 12
    assert len({s["url"] for s in data["sources"]}) == 19
    videos = [s for s in data["sources"] if s["kind"] == "video"]
    assert all(len(classify(v["url"]).video_id or "") == 11 for v in videos)
    priorities = [next(s["priority"] for s in data["sources"] if s["id"] == r.catalog_id) for r in enabled]
    assert priorities == sorted(priorities)
    assert enabled[0].curation["topic"] == "unity-grid"


def test_catalog_rejects_ambiguous_or_invalid_blocks():
    with pytest.raises(InputError):
        parse_catalog("sem marcadores")
    block = "<!-- RAG_SOURCE_CATALOG_START -->\n```json\n{}\n```\n<!-- RAG_SOURCE_CATALOG_END -->"
    with pytest.raises(InputError):
        parse_catalog(block + block)
    with pytest.raises(InputError, match="catalog_schema"):
        parse_catalog(block)


def test_manifest_v1_from_the_ui_is_revalidated(tmp_path):
    manifest = {"schema_version": 1, "status": "draft", "collection_executed": False, "sources": [
        {"original_url": "https://docs.unity3d.com/Manual/", "canonical_url": "https://evil.example/", "kind": "video"},
    ]}
    items = from_manifest(manifest)
    assert [i.original_url for i in items] == ["https://docs.unity3d.com/Manual/"]  # kind/canonical ignorados
    with pytest.raises(InputError):
        from_manifest({"schema_version": 2, "sources": []})
    with pytest.raises(InputError):
        from_manifest({"schema_version": 1, "sources": [{"original_url": "https://a.com"}] * 201})
    path = tmp_path / "lista.txt"
    path.write_text("https://a.com\n\n https://b.com \n", encoding="utf-8")
    assert [i.original_url for i in load_input(path)] == ["https://a.com", "https://b.com"]
