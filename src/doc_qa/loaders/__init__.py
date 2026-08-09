"""Format-dispatching loader registry.

M5 adds DOCX/PPTX/CSV/TXT loaders here; the rest of the pipeline only ever
sees TextBlocks and never asks which format they came from.
"""

from __future__ import annotations

from pathlib import Path

from doc_qa.errors import UnsupportedFormatError

from .base import DocumentLoader, TextBlock
from .pdf import PdfLoader

_LOADERS: tuple[DocumentLoader, ...] = (PdfLoader(),)


def loader_for(path: Path | str) -> DocumentLoader:
    """Return the loader that handles ``path``'s format."""
    suffix = Path(path).suffix.lower()
    for loader in _LOADERS:
        if suffix in loader.suffixes:
            return loader
    supported = ", ".join(sorted(s for ld in _LOADERS for s in ld.suffixes))
    raise UnsupportedFormatError(f"No loader for '{suffix or path}' (supported: {supported})")


__all__ = ["DocumentLoader", "PdfLoader", "TextBlock", "loader_for"]
