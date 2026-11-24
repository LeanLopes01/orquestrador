from io import BytesIO
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject


def pdf_bytes(text):
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    content = DecodedStreamObject()
    content.set_data(f'BT /F1 12 Tf 20 200 Td ({text}) Tj ET'.encode())
    page[NameObject('/Contents')] = writer._add_object(content)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_pdf_index_update_remove(make_rag):
    rag = make_rag()
    path = rag.config.docs_root / 'manual.pdf'
    path.write_bytes(pdf_bytes('The dragon uses hexagonal movement.'))
    assert rag.docs.index_documents().added == 1
    assert rag.docs.index_documents().skipped == 1
    sources = rag.retrieve('dragon movement').sources
    assert any(s.section == 'Página 1' and 'dragon' in s.text for s in sources)
    path.write_bytes(pdf_bytes('The knight uses square movement.'))
    assert rag.docs.index_documents().updated == 1
    path.unlink()
    assert rag.docs.index_documents().removed == 1


def test_bad_pdf_does_not_stop_other_files(make_rag):
    rag = make_rag()
    (rag.config.docs_root / 'broken.pdf').write_bytes(b'not a pdf')
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.write(rag.config.docs_root / 'scanned.pdf')
    (rag.config.docs_root / 'valid.txt').write_text('A valid document')
    report = rag.docs.index_documents()
    assert report.added == 1
    assert len(report.errors) == 2
    assert any('OCR' in e for e in report.errors)
