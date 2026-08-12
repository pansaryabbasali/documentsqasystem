"""Ingestion tests: real loaders + real dataset, fake embedder, in-memory store."""

from pathlib import Path
from uuid import uuid4

from doc_qa.embeddings import Embedder
from doc_qa.ingest import ingest_directory
from doc_qa.store import VectorStore

DATASET = Path(__file__).resolve().parent.parent / "dataset"


class FakeEmbedder(Embedder):
    """Deterministic 8-dim vectors from text content; no model, no network."""

    def __init__(self) -> None:
        super().__init__(model_name="fake")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float((hash(t) >> shift) % 97) / 97 for shift in range(8)] for t in texts]


def test_ingest_dataset_indexes_pdfs_and_skips_rest() -> None:
    store = VectorStore(collection=f"ingest_{uuid4().hex}")
    stats = ingest_directory(
        DATASET, store, FakeEmbedder(), count_tokens=lambda t: len(t.split())
    )
    assert stats.files_indexed == 6  # the six PDFs (other formats arrive in M5)
    assert stats.chunks_indexed == store.count() > 6
    skipped_suffixes = {Path(name).suffix for name in stats.skipped}
    assert skipped_suffixes == {".docx", ".pptx", ".csv", ".txt"}


def test_missing_dataset_dir_fails_loudly() -> None:
    import pytest

    from doc_qa.errors import DocQAError

    with pytest.raises(DocQAError, match="not found"):
        ingest_directory(
            Path("no/such/dir"),
            VectorStore(collection=f"ingest_{uuid4().hex}"),
            FakeEmbedder(),
            count_tokens=lambda t: len(t.split()),
        )


def test_ingested_chunks_are_retrievable_with_provenance() -> None:
    store = VectorStore(collection=f"ingest_{uuid4().hex}")
    embedder = FakeEmbedder()
    ingest_directory(DATASET, store, embedder, count_tokens=lambda t: len(t.split()))
    results = store.query(embedder.embed_texts(["wear ring clearance"])[0], k=3)
    assert len(results) == 3
    for r in results:
        assert r.chunk.source.endswith(".pdf")
        assert r.chunk.locator.startswith("page ")
