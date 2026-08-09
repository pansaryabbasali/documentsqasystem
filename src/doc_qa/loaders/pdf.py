"""PDF extraction via pdfplumber, one TextBlock per page.

Text is read in the PDF's internal drawing order (``use_text_flow=True``)
rather than geometrically sorted by position. Reason, found by the M2
extraction harness: some dataset tables draw over-wide cell text that
physically overlaps the neighboring column, and geometric sorting zips the
overlapping characters into garbage ("Cavitation" + "or grinding" →
"oCra gvritinadtioinng"). Drawing order preserves each cell's text intact.
Trade-off: drawing order can scramble multi-column *layouts*; this corpus is
single-column throughout, so reading order is safe here. Revisit for the
harder-documents project.

``(cid:N)`` tokens — glyphs whose font ships no Unicode mapping (bullets in
these generated PDFs) — are normalized to "•".
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import pdfplumber

from .base import TextBlock

_CID_ARTIFACT = re.compile(r"\(cid:\d+\)")


class PdfLoader:
    """Extracts text-native PDFs page by page (no OCR — out of scope for this corpus)."""

    suffixes: tuple[str, ...] = (".pdf",)

    def load(self, path: Path) -> Iterator[TextBlock]:
        with pdfplumber.open(path) as pdf:
            for number, page in enumerate(pdf.pages, start=1):
                text = page.extract_text(use_text_flow=True) or ""
                text = _CID_ARTIFACT.sub("•", text)
                if text.strip():
                    yield TextBlock(text=text, source=path.name, locator=f"page {number}")
