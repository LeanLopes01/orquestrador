"""Bounded local extraction; PDFs preserve page numbers as chunk sections."""
from io import BytesIO
from pathlib import Path

from .paths import ReadError, decode_text

SUPPORTED = {'.pdf', '.md', '.txt', '.csv', '.tsv', '.json', '.yaml', '.yml', '.xml', '.log'}


def extract_text(path: Path, data: bytes, encoding: str) -> str:
    if path.suffix.lower() != '.pdf':
        return decode_text(data, encoding).replace('\r\n', '\n')
    try:
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            raise ValueError('PDF protegido por senha; forneça uma cópia desbloqueada.')
        if len(reader.pages) > 1000:
            raise ValueError('PDF excede o limite de 1000 páginas.')
        parts = []
        total = 0
        for number, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ''
            if not text.strip():
                continue
            total += len(text)
            if total > 4_000_000:
                raise ValueError('Texto extraído excede 4 milhões de caracteres.')
            # Keep page sections unambiguous even when source text contains headings.
            text = '\n'.join(line.lstrip('#') for line in text.splitlines())
            parts.append(f'# Página {number}\n\n{text}')
        if not parts:
            raise ValueError('PDF sem texto extraível. Aplique OCR antes de indexar; o arquivo não contém texto.')
        return '\n\n'.join(parts)
    except Exception as exc:
        raise ReadError('pdf_extraction', f'Falha ao extrair PDF: {exc}') from exc
