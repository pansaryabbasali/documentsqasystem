"""Loader contract: every format yields TextBlocks with provenance attached.

Provenance (source document + human-readable locator) is captured at extraction
time because citations are a hard success criterion — it cannot be reliably
reconstructed after chunking.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class TextBlock:
    """One provenance-bearing unit of extracted text (a page, slide, or row)."""

    text: str
    source: str  # document file name, e.g. "AF-4500_Series_IOM_Manual.pdf"
    locator: str  # citation locator, e.g. "page 7", "slide 3", "row 12"


@runtime_checkable
class DocumentLoader(Protocol):
    """Anything that turns a file into provenance-tagged text blocks."""

    suffixes: tuple[str, ...]

    def load(self, path: Path) -> Iterator[TextBlock]: ...
