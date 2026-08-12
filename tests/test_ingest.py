"""Ingestion tests: real loaders + real dataset, fake embedder, in-memory store."""

from pathlib import Path
from uuid import uuid4

from conftest import FakeEmbedder
from doc_qa.ingest import ingest_directory
from doc_qa.store import VectorStore

DATASET = Path(__file__).resolve().parent.parent / "dataset"


def test_ingest_dataset_indexes_all_twelve_documents() -> None:
    store = VectorStore(collection=f"ingest_{uuid4().hex}")
    stats = ingest_directory(
        DATASET, store, FakeEmbedder(), count_tokens=lambda t: len(t.split())
    )
    assert stats.files_indexed == 12  # all five formats have loaders as of M5
    assert stats.skipped == []
    assert stats.chunks_indexed == store.count() > 12


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
        assert Path(r.chunk.source).suffix in {".pdf", ".docx", ".pptx", ".csv", ".txt"}
        assert r.chunk.locator, "every chunk must be citable, whatever its format"
