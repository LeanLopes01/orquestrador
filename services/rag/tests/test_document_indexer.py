import pytest
from conftest import copy_fixture

from unity_rag.document_indexer import parse_header


def test_header_only_from_first_block():
    text = "Fonte: https://x.org/a\nTipo: Vídeo\nData de Extração: 2026-10-21T10:00:00-03:00\nIdioma: pt\n\n---\n\n# T\n\nCorpo\nFonte: falsa\n---\n"
    meta, body, offset = parse_header(text)
    assert meta == {"source_url": "https://x.org/a", "source_type": "video",
                    "extracted_at": "2026-10-21T10:00:00-03:00", "language": "pt"}
    assert body.startswith("\n# T") and "Fonte: falsa" in body
    assert text[offset:] == body
    assert parse_header("# Sem cabeçalho\n---\n")[0] == {}


def test_documents_keep_provenance_in_every_chunk_and_full_coverage(make_rag):
    rag = make_rag()
    docs = rag.config.docs_root
    copy_fixture("regras-grid.md", docs / "regras-grid.md")
    copy_fixture("nota-manual.txt", docs / "nota-manual.txt")
    long = docs / "longo.md"
    words = [f"palavra{i}" for i in range(600)]
    long.write_text("# Longo\n\n" + " ".join(words), encoding="utf-8")
    (docs / ".tmp-parcial.md").write_text("não indexar")
    report = rag.submit_index("documents").result()["documents"]
    assert report["added"] == 3 and not report["errors"]
    rows = rag.store.get(where=rag.store.where("dicevtt", "documentation"))
    grid = [m for m in rows["metadatas"] if m["relpath"] == "regras-grid.md"]
    assert grid and all(m["source_url"] == "https://example.com/regras-grid" and m["source_type"] == "article"
                        and m["extracted_at"] == "2026-10-21T15:30:00-03:00" for m in grid)
    assert not any("Fonte: https://example.com" in d for d in rows["documents"])  # cabeçalho fora do embedding
    manual = [m for m in rows["metadatas"] if m["relpath"] == "nota-manual.txt"]
    assert manual and "source_url" not in manual[0] and manual[0]["provenance"] == "local"
    chunks = [d for d, m in zip(rows["documents"], rows["metadatas"]) if m["relpath"] == "longo.md"]
    covered = set(" ".join(chunks).split())
    assert set(words) <= covered  # nenhum token perdido por truncamento


def test_shrinking_document_removes_excess_chunks(make_rag):
    rag = make_rag()
    path = rag.config.docs_root / "doc.md"
    path.write_text("# Doc\n\n" + " ".join(f"w{i}" for i in range(400)), encoding="utf-8")
    rag.submit_index("documents").result()
    before = rag.store.count("dicevtt", "documentation")
    path.write_text("# Doc\n\nCurto agora.", encoding="utf-8")
    rag.submit_index("documents").result()
    assert before > 1 and rag.store.count("dicevtt", "documentation") == 1
    path.unlink()
    rag.submit_index("documents").result()
    assert rag.store.count("dicevtt", "documentation") == 0


def test_interrupted_replacement_recovers_from_journal(make_rag, monkeypatch):
    rag = make_rag()
    path = rag.config.docs_root / "doc.md"
    path.write_text("# Doc\n\n" + " ".join(f"v1_{i}" for i in range(300)), encoding="utf-8")
    rag.submit_index("documents").result()
    path.write_text("# Doc\n\nversão nova curta", encoding="utf-8")
    original = rag.store.delete

    def crash(ids):
        raise RuntimeError("queda simulada")

    monkeypatch.setattr(rag.store, "delete", crash)
    with pytest.raises(RuntimeError):
        rag.docs.index_file(path)
    assert rag.docs.recovering
    result = rag.retrieve("versão nova")
    assert any(w.startswith("documents_recovering") for w in result.warnings)
    assert not any(s.kind == "documentation" for s in result.sources)  # nunca versões misturadas
    monkeypatch.setattr(rag.store, "delete", original)
    report = rag.docs.recover()
    assert report.updated == 1 and not rag.docs.recovering
    texts = rag.store.get(where=rag.store.where("dicevtt", "documentation"))["documents"]
    assert len(texts) == 1 and texts[0].endswith("versão nova curta")


def test_changed_markdown_needs_reindex(make_rag):
    rag = make_rag()
    path = copy_fixture("regras-grid.md", rag.config.docs_root / "regras-grid.md")
    rag.submit_index("documents").result()
    path.write_text(path.read_text(encoding="utf-8") + "\nNova regra.", encoding="utf-8")
    result = rag.retrieve("custo de movimento por célula")
    assert any(w.startswith("document_needs_reindex") for w in result.warnings)
    assert not any(s.kind == "documentation" for s in result.sources)
    rag.submit_index("documents").result()
    assert any(s.kind == "documentation" for s in rag.retrieve("custo de movimento por célula").sources)


def test_invalid_encoding_is_reported(make_rag):
    rag = make_rag()
    (rag.config.docs_root / "ruim.md").write_bytes(b"# T\n\n\x81\x8d\x8f\x90\x9d inv\xe1lido")
    report = rag.submit_index("documents").result()["documents"]
    assert report["errors"] and "UTF-8" in report["errors"][0]
