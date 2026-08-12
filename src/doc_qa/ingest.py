"""Ingestion pipeline: files → provenance-tagged blocks → chunks → vectors → store.

Formats without a registered loader are counted and skipped, not fatal — the
corpus is mixed and loaders arrive milestone by milestone (M5 completes them).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .chunking import Chunk, chunk_blocks
from .embeddings import Embedder
from .errors import DocQAError, UnsupportedFormatError
from .loaders import loader_for
from .store import VectorStore


@dataclass
class IngestStats:
    files_indexed: int = 0
    chunks_indexed: int = 0
    skipped: list[str] = field(default_factory=list)  # files with no loader yet


def ingest_file(
    path: Path,
    store: VectorStore,
    embedder: Embedder,
    *,
    count_tokens: Callable[[str], int],
) -> int:
    """Index one file; returns the number of chunks stored.

    Raises UnsupportedFormatError when no loader handles the format —
    single-file ingestion (e.g. an upload) must fail loudly, unlike a
    directory sweep where skipping is the right policy.
    """
    chunks: list[Chunk] = chunk_blocks(loader_for(path).load(path), count_tokens=count_tokens)
    if chunks:
        store.add(chunks, embedder.embed_texts([c.text for c in chunks]))
    return len(chunks)


def ingest_directory(
    dataset_dir: Path,
    store: VectorStore,
    embedder: Embedder,
    *,
    count_tokens: Callable[[str], int],
) -> IngestStats:
    """Index every supported file under ``dataset_dir`` (recursive, deterministic order)."""
    dataset_dir = Path(dataset_dir)
    if not dataset_dir.is_dir():
        # rglob on a missing dir yields nothing — that would report "0 files
        # indexed" as success. A wrong path must fail loudly, not quietly.
        raise DocQAError(f"dataset directory not found: {dataset_dir.resolve()}")
    stats = IngestStats()
    for path in sorted(p for p in dataset_dir.rglob("*") if p.is_file()):
        try:
            indexed = ingest_file(path, store, embedder, count_tokens=count_tokens)
        except UnsupportedFormatError:
            stats.skipped.append(path.name)
            continue
        if indexed:
            stats.files_indexed += 1
            stats.chunks_indexed += indexed
    return stats
