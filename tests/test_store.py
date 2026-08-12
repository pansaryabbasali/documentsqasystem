"""VectorStore tests: in-memory Chroma, hand-made embeddings, fully offline.

Each test gets a uniquely named collection: Chroma's ephemeral client shares
one in-process system, so a fixed name would leak state between tests (found
the hard way — see project_summary incident log).
"""

from uuid import uuid4

import pytest

from doc_qa.chunking import Chunk
from doc_qa.store import VectorStore


def fresh_store() -> VectorStore:
    return VectorStore(collection=f"test_{uuid4().hex}")


def make_chunk(text: str, source: str = "iom.pdf", locator: str = "page 1") -> Chunk:
    return Chunk(text=text, source=source, locator=locator, ordinal=0)


def test_query_ranks_by_cosine_similarity() -> None:
    store = fresh_store()
    store.add(
        [
            make_chunk("seal replacement", locator="page 1"),
            make_chunk("warranty terms", locator="page 2"),
            make_chunk("torque values", locator="page 3"),
        ],
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.7, 0.7, 0.0]],
    )
    results = store.query([1.0, 0.0, 0.0], k=3)
    assert [r.chunk.locator for r in results] == ["page 1", "page 3", "page 2"]
    assert results[0].score == pytest.approx(1.0)
    assert results[0].score > results[1].score > results[2].score


def test_provenance_roundtrips_through_storage() -> None:
    store = fresh_store()
    original = Chunk(text="Flash point 220°C", source="sds.pdf", locator="page 2", ordinal=3)
    store.add([original], [[0.5, 0.5, 0.0]])
    assert store.query([0.5, 0.5, 0.0], k=1)[0].chunk == original


def test_query_k_clamped_to_collection_size() -> None:
    store = fresh_store()
    assert store.query([1.0, 0.0], k=5) == []  # empty store: no crash, no results
    store.add([make_chunk("only entry")], [[1.0, 0.0]])
    assert len(store.query([1.0, 0.0], k=50)) == 1


def test_mismatched_lengths_rejected() -> None:
    with pytest.raises(ValueError, match="2 chunks but 1"):
        fresh_store().add([make_chunk("a"), make_chunk("b")], [[1.0, 0.0]])


def test_reingesting_same_chunk_ids_does_not_duplicate() -> None:
    store = fresh_store()
    chunk = make_chunk("stable identity")
    store.add([chunk], [[1.0, 0.0]])
    store.add([chunk], [[1.0, 0.0]])  # same source|locator|ordinal → same id
    assert store.count() == 1
