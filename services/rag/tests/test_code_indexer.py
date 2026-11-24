from pathlib import Path

from conftest import copy_fixture

from unity_rag.csharp_summary import summarize


def test_summary_extracts_only_name_class_and_associated_comments():
    src = (Path(__file__).parent / "fixtures" / "NetworkManager.cs").read_text(encoding="utf-8")
    summary = summarize(src, "NetworkManager.cs")
    assert summary.main_class == "NetworkManager"  # coincide com o arquivo, não Helper
    assert "Gerencia lobbies Steamworks" in summary.class_doc
    assert "LobbyData" in summary.class_doc  # <see cref> vira texto
    assert "Cabeçalho" in summary.header
    text = summary.text()
    assert "comentário interno" not in text
    assert "CriarLobby" not in text
    names = {t.name for t in summary.types}
    assert not names & {"NotAClass", "AlsoNot", "InsideRaw", "Nope"}  # strings não são declarações


def test_summary_without_comment_does_not_invent_description():
    summary = summarize("public class SemComentario { }", "SemComentario.cs")
    assert summary.text() == "Arquivo: SemComentario.cs. Classe: SemComentario."


def test_incomplete_syntax_and_no_class_keep_the_file():
    summary = summarize('/// doc\npublic class Meia {\n  var s = "sem fim\n', "Meia.cs")
    assert summary.main_class == "Meia"
    assert summarize("// só comentário", "Vazio.cs").main_class is None


def test_index_stores_summary_not_body_and_skips_meta(make_rag):
    rag = make_rag()
    scripts = rag.config.scripts_root
    copy_fixture("NetworkManager.cs", scripts / "Net" / "NetworkManager.cs")
    copy_fixture("SemComentario.cs", scripts / "Pasta Com Espaço" / "Ação" / "SemComentario.CS")
    (scripts / "Net" / "NetworkManager.cs.meta").write_text("guid: 1")
    (scripts / "Library").mkdir()
    (scripts / "Library" / "Ignorado.cs").write_text("class Ignorado {}")
    report = rag.submit_index("code").result()["code"]
    assert report["added"] == 2 and not report["errors"]
    rows = rag.store.get(where=rag.store.where("dicevtt", "code_pointer"))
    assert len(rows["ids"]) == 2
    joined = " ".join(rows["documents"])
    assert "CriarLobby" not in joined and "Debug.Log" not in joined
    assert "Gerencia lobbies Steamworks" in joined
    assert all(m["kind"] == "code_pointer" and m["project_id"] == "dicevtt" for m in rows["metadatas"])


def test_body_change_updates_metadata_without_new_embedding(make_rag):
    rag = make_rag()
    path = copy_fixture("NetworkManager.cs", rag.config.scripts_root / "NetworkManager.cs")
    rag.submit_index("code").result()
    calls = rag._embedder.calls
    path.write_text(path.read_text(encoding="utf-8").replace("Debug.Log(x);", "Debug.Log(x + 1);"), encoding="utf-8")
    assert rag.code.index_file(path) == "metadata"
    assert rag._embedder.calls == calls
    path.write_text(path.read_text(encoding="utf-8").replace("Gerencia lobbies", "Coordena lobbies"), encoding="utf-8")
    assert rag.code.index_file(path) == "updated"
    assert rag._embedder.calls == calls + 1


def test_restart_reconciles_offline_changes_without_orphans(make_rag, tmp_path):
    rag = make_rag()
    scripts = rag.config.scripts_root
    keep = copy_fixture("NetworkManager.cs", scripts / "NetworkManager.cs")
    gone = copy_fixture("SemComentario.cs", scripts / "SemComentario.cs")
    rag.submit_index("code").result()
    rag.close()
    gone.unlink()
    (scripts / "Novo.cs").write_text("/// Novo script.\npublic class Novo {}", encoding="utf-8")
    keep.write_text(keep.read_text(encoding="utf-8") + "\n// fim", encoding="utf-8")
    rag2 = make_rag()
    report = rag2.submit_index("code").result()["code"]
    assert report["removed"] == 1 and report["added"] == 1
    assert rag2.store.count("dicevtt", "code_pointer") == 2


def test_unavailable_root_is_not_mass_deletion(make_rag):
    rag = make_rag()
    copy_fixture("NetworkManager.cs", rag.config.scripts_root / "NetworkManager.cs")
    rag.submit_index("code").result()
    rag.code.root = rag.config.scripts_root / "nao-existe"
    report = rag.code.reconcile()
    assert report.errors and report.removed == 0
    assert rag.store.count("dicevtt", "code_pointer") == 1
