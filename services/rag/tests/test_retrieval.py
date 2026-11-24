import os

import pytest
from conftest import copy_fixture

from unity_rag.retrieval import QueryError


def test_body_change_is_seen_before_the_watcher_updates(make_rag):
    rag = make_rag()
    path = copy_fixture("NetworkManager.cs", rag.config.scripts_root / "NetworkManager.cs")
    rag.submit_index("code").result()
    path.write_text(path.read_text(encoding="utf-8").replace("Debug.Log(x);", "Debug.Log(\"CODIGO_NOVO\");"),
                    encoding="utf-8")
    result = rag.retrieve("lobbies Steamworks sincronização P2P")
    source = next(s for s in result.sources if s.kind == "code_pointer")
    assert "CODIGO_NOVO" in source.text  # lido agora do disco, não do índice
    assert source.state == "stale_summary"
    assert source.full_file and source.relpath == "Assets/Scripts/NetworkManager.cs"


def test_code_and_rule_in_the_same_answer_with_stable_ids(make_rag):
    rag = make_rag()
    copy_fixture("NetworkManager.cs", rag.config.scripts_root / "NetworkManager.cs")
    copy_fixture("regras-grid.md", rag.config.docs_root / "regras-grid.md")
    rag.submit_index("all").result()
    result = rag.retrieve("movimento no grid e sincronização P2P do host")
    kinds = {s.kind for s in result.sources}
    assert kinds == {"code_pointer", "documentation"}
    assert [s.id for s in result.sources] == [f"S{i}" for i in range(1, len(result.sources) + 1)]
    doc = next(s for s in result.sources if s.kind == "documentation")
    assert doc.provenance["source_url"] == "https://example.com/regras-grid"


def test_deleted_file_between_search_and_read_is_a_warning_with_backfill(make_rag):
    rag = make_rag(code_top_k=1)
    first = copy_fixture("NetworkManager.cs", rag.config.scripts_root / "NetworkManager.cs")
    copy_fixture("SemComentario.cs", rag.config.scripts_root / "SemComentario.cs")
    rag.submit_index("code").result()
    first.unlink()
    result = rag.retrieve("NetworkManager lobbies Steamworks")
    assert any(w.startswith("source_missing") for w in result.warnings)
    assert [s.relpath for s in result.sources if s.kind == "code_pointer"] == ["Assets/Scripts/SemComentario.cs"]


def test_pointer_outside_root_is_rejected(make_rag, tmp_path):
    rag = make_rag()
    outside = tmp_path / "fora.cs"
    outside.write_text("/// Segredo fora da raiz.\npublic class Fora {}", encoding="utf-8")
    vector = rag._embedder.encode(["Arquivo: fora.cs. Classe: Fora."])[0]
    rag.store.upsert(["code:forjado"], [vector], ["Arquivo: fora.cs. Classe: Fora."],
                     [{"kind": "code_pointer", "project_id": "dicevtt", "filepath": str(outside), "filename": "fora.cs"}])
    result = rag.retrieve("Arquivo fora Classe Fora")
    assert any(w.startswith("pointer_outside_root") for w in result.warnings)
    assert all("Segredo" not in s.text for s in result.sources)


def test_project_isolation(make_rag):
    rag = make_rag()
    vector = rag._embedder.encode(["regra de outro projeto"])[0]
    rag.store.upsert(["doc:outro:0"], [vector], ["regra de outro projeto"],
                     [{"kind": "documentation", "project_id": "outro", "filepath": "x", "doc_hash": "h"}])
    assert rag.retrieve("regra de outro projeto").sources == []


def test_explicit_mention_comes_first(make_rag):
    rag = make_rag()
    copy_fixture("NetworkManager.cs", rag.config.scripts_root / "NetworkManager.cs")
    copy_fixture("SemComentario.cs", rag.config.scripts_root / "SemComentario.cs")
    rag.submit_index("code").result()
    result = rag.retrieve("O que faz SemComentario.cs com lobbies Steamworks?")
    assert result.sources[0].relpath.endswith("SemComentario.cs")
    assert any(w.startswith("mention_not_indexed") for w in rag.retrieve("e o Inexistente.cs?").warnings)


def test_empty_index_and_invalid_queries(make_rag):
    rag = make_rag()
    result = rag.retrieve("qualquer coisa")
    assert result.sources == [] and any(w.startswith("no_context") for w in result.warnings)
    with pytest.raises(QueryError):
        rag.retrieve("   ")
    with pytest.raises(QueryError):
        rag.retrieve("x" * 5000)


@pytest.mark.skipif(os.name != "nt", reason="bloqueio de arquivo do Windows")
def test_locked_file_is_reported(make_rag):
    import msvcrt

    rag = make_rag(code_top_k=1)
    path = copy_fixture("SemComentario.cs", rag.config.scripts_root / "SemComentario.cs")
    rag.submit_index("code").result()
    with open(path, "r+b") as handle:
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, path.stat().st_size)
        result = rag.retrieve("SemComentario Valor")
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, path.stat().st_size)
    assert any(w.startswith("source_unreadable") for w in result.warnings)
    assert not [s for s in result.sources if s.kind == "code_pointer"]
