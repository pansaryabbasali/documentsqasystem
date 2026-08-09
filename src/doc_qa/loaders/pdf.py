"""PDF extraction via pdfplumber, one TextBlock per page."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pdfplumber

from .base import TextBlock


class PdfLoader:
    """Extracts text-native PDFs page by page (no OCR — out of scope for this corpus)."""

    suffixes: tuple[str, ...] = (".pdf",)

    def load(self, path: Path) -> Iterator[TextBlock]:
        with pdfplumber.open(path) as pdf:
            for number, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    yield TextBlock(text=text, source=path.name, locator=f"page {number}")
