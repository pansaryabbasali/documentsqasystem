"""Provenance-preserving chunking: token-budgeted, with an injected token counter.

Chunks never cross a TextBlock boundary (a page/slide/row), so every chunk's
citation locator stays exact. The trade-off — a sentence spanning two pages is
split — is accepted because citation precision is a hard success criterion and
retrieval overlap compensates.

The token counter is injected (a plain callable) rather than imported here:
production passes the embedding model's real tokenizer (see tokenization.py),
tests pass a deterministic fake, and the M3 bake-off can pass each candidate
model's own tokenizer without touching this module.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from .loaders.base import TextBlock

DEFAULT_CHUNK_TOKENS = 500
DEFAULT_OVERLAP_TOKENS = 50


@dataclass(frozen=True)
class Chunk:
    """A retrieval unit that still knows exactly where it came from."""

    text: str
    source: str
    locator: str
    ordinal: int  # position of this chunk within its parent block

    @property
    def ref(self) -> str:
        """Human-readable citation reference, e.g. 'IOM_Manual.pdf — page 7'."""
        return f"{self.source} — {self.locator}"


def chunk_blocks(
    blocks: Iterable[TextBlock],
    *,
    count_tokens: Callable[[str], int],
    chunk_tokens: int = DEFAULT_CHUNK_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> list[Chunk]:
    """Split blocks into token-bounded chunks, preserving each block's provenance."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_tokens,
        chunk_overlap=overlap_tokens,
        length_function=count_tokens,
    )
    chunks: list[Chunk] = []
    for block in blocks:
        for ordinal, piece in enumerate(splitter.split_text(block.text)):
            chunks.append(
                Chunk(text=piece, source=block.source, locator=block.locator, ordinal=ordinal)
            )
    return chunks
