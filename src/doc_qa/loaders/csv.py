"""CSV extraction (stdlib), one TextBlock per data row.

Each row is rendered as self-contained "Header: value" pairs so a retrieved
chunk carries its column names with it — a bare "650,110,90" embeds and
reads as noise; "Model: AF-4520; Max_Flow_m3h: 650; ..." answers questions.
Locator is the 1-based DATA row number (header excluded).
"""

from __future__ import annotations

import csv
from collections.abc import Iterator
from pathlib import Path

from .base import TextBlock


class CsvLoader:
    suffixes: tuple[str, ...] = (".csv",)

    def load(self, path: Path) -> Iterator[TextBlock]:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            rows = [row for row in csv.reader(handle) if any(cell.strip() for cell in row)]
        if len(rows) < 2:  # header only (or empty): nothing citable
            return
        header, *data = rows
        for number, row in enumerate(data, start=1):
            # strict=False: ragged rows are real-world CSV; pair what exists
            pairs = "; ".join(
                f"{h.strip()}: {v.strip()}" for h, v in zip(header, row, strict=False)
            )
            yield TextBlock(text=pairs, source=path.name, locator=f"row {number}")
