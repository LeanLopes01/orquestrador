import pytest
from conftest import FIXTURES

from rag_ingestion.formatter import build_markdown, parse_header
from rag_ingestion.models import ExtractedDocument, SourceFailure
from rag_ingestion.urls import classify
from rag_ingestion.web_extractor import extract_article
from rag_ingestion.youtube_extractor import format_transcript


def test_article_keeps_headings_tables_lists_and_code():
    html = (FIXTURES / "artigo.html").read_text(encoding="utf-8")
    doc = extract_article(html, "https://exemplo.org/grid", min_chars=120)
    assert "Grid fictício" in doc.title
    body = doc.body
    assert "Conversão" in body and "arredonde para baixo" in body
    assert "|" in body  # tabela em Markdown
    assert "FloorToInt" in body  # código preservado
    assert "posição" in body  # acentos intactos
    assert "Rodapé" not in body and "Menu Início" not in body


def test_js_shell_is_content_unavailable():
    with pytest.raises(SourceFailure) as exc:
        extract_article((FIXTURES / "vazio.html").read_text(encoding="utf-8"), None, min_chars=120)
    assert exc.value.reason == "content_unavailable"


def test_transcript_paragraphs_with_timestamps_and_caption_kind():
    segments = [{"text": "olá pessoal", "start": 0.0, "duration": 2.0},
                {"text": "olá pessoal", "start": 2.0, "duration": 1.0},  # repetição consecutiva
                {"text": "hoje vamos falar de tilemaps", "start": 3.0, "duration": 4.0},
                {"text": "segunda parte", "start": 75.0, "duration": 3.0}]
    doc = format_transcript({"video_id": "tywt9tOubEY", "language_code": "pt", "is_generated": True, "segments": segments})
    assert doc.caption == "automática" and doc.language == "pt"
    assert "[00:00] olá pessoal hoje vamos falar de tilemaps" in doc.body
    assert "[01:15] segunda parte" in doc.body
    assert doc.body.count("olá pessoal") == 1


def test_markdown_round_trip_header():
    spec = classify("https://www.youtube.com/watch?v=tywt9tOubEY")
    doc = ExtractedDocument("Vídeo tywt9tOubEY", "[00:00] texto", language="pt-BR", caption="manual")
    markdown = build_markdown(doc, spec, extracted_at="2026-10-21T15:30:00-03:00", acquired_at="2026-10-21T15:00:00-03:00")
    assert markdown.startswith("Fonte: https://www.youtube.com/watch?v=tywt9tOubEY\nTipo: Vídeo\nData de Extração: ")
    fields, body = parse_header(markdown)
    assert fields["Source ID"] == spec.source_id and fields["Idioma"] == "pt-BR" and fields["Legenda"] == "manual"
    assert body.startswith("# Vídeo tywt9tOubEY")
    with pytest.raises(ValueError):
        build_markdown(doc, spec, extracted_at="2026\n-10", acquired_at="x")
