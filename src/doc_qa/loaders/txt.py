"""Plain-text extraction (stdlib), one TextBlock for the whole file.

A text memo has no pages, slides, or rows; pretending otherwise would
manufacture fake precision. The locator is honest: "full document". The
chunker still splits oversized files — every chunk keeps this locator.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from .base import TextBlock


class TxtLoader:
    suffixes: tuple[str, ...] = (".txt",)

    def load(self, path: Path) -> Iterator[TextBlock]:
        text = path.read_text(encoding="utf-8").strip()
        if text:
            yield TextBlock(text=text, source=path.name, locator="full document")
