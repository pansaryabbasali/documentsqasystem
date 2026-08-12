"""Format-dispatching loader registry.

All five corpus formats are registered; the rest of the pipeline only ever
sees TextBlocks and never asks which format they came from.
"""

from __future__ import annotations

from pathlib import Path

from doc_qa.errors import UnsupportedFormatError

from .base import DocumentLoader, TextBlock
from .csv import CsvLoader
from .docx import DocxLoader
from .pdf import PdfLoader
from .pptx import PptxLoader
from .txt import TxtLoader

_LOADERS: tuple[DocumentLoader, ...] = (
    PdfLoader(),
    DocxLoader(),
    PptxLoader(),
    CsvLoader(),
    TxtLoader(),
)


def loader_for(path: Path | str) -> DocumentLoader:
    """Return the loader that handles ``path``'s format."""
    suffix = Path(path).suffix.lower()
    for loader in _LOADERS:
        if suffix in loader.suffixes:
            return loader
    supported = ", ".join(sorted(s for ld in _LOADERS for s in ld.suffixes))
    raise UnsupportedFormatError(f"No loader for '{suffix or path}' (supported: {supported})")


__all__ = [
    "CsvLoader",
    "DocumentLoader",
    "DocxLoader",
    "PdfLoader",
    "PptxLoader",
    "TextBlock",
    "TxtLoader",
    "loader_for",
]
