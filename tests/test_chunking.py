"""Chunking tests with an injected fake token counter (offline, deterministic)."""

from doc_qa.chunking import Chunk, chunk_blocks
from doc_qa.loaders.base import TextBlock


def words(text: str) -> int:
    """Fake token counter: whitespace words. Deterministic, no downloads."""
    return len(text.split())


def test_short_block_stays_whole_with_provenance() -> None:
    block = TextBlock(text="Torque the casing bolts to 95 Nm.", source="iom.pdf", locator="page 7")
    expected = Chunk(text=block.text, source="iom.pdf", locator="page 7", ordinal=0)
    assert chunk_blocks([block], count_tokens=words) == [expected]


def test_long_block_splits_within_token_budget() -> None:
    text = "\n\n".join(f"Sentence number {i} about mechanical seals." for i in range(200))
    chunks = chunk_blocks(
        [TextBlock(text=text, source="iom.pdf", locator="page 3")],
        count_tokens=words,
        chunk_tokens=100,
        overlap_tokens=10,
    )
    assert len(chunks) > 1
    assert all(words(c.text) <= 100 for c in chunks)
    assert all(c.locator == "page 3" for c in chunks), "provenance must survive splitting"
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))


def test_chunks_never_cross_block_boundaries() -> None:
    blocks = [
        TextBlock(text="alpha " * 30, source="a.pdf", locator="page 1"),
        TextBlock(text="omega " * 30, source="a.pdf", locator="page 2"),
    ]
    chunks = chunk_blocks(blocks, count_tokens=words, chunk_tokens=40, overlap_tokens=0)
    for chunk in chunks:
        assert ("alpha" in chunk.text) != ("omega" in chunk.text), "page contents must not mix"
        assert chunk.locator == ("page 1" if "alpha" in chunk.text else "page 2")


def test_overlap_repeats_trailing_context() -> None:
    text = " ".join(f"w{i}" for i in range(120))
    chunks = chunk_blocks(
        [TextBlock(text=text, source="a.pdf", locator="page 1")],
        count_tokens=words,
        chunk_tokens=50,
        overlap_tokens=10,
    )
    assert len(chunks) >= 2
    tail_of_first = set(chunks[0].text.split()[-10:])
    head_of_second = set(chunks[1].text.split()[:10])
    assert tail_of_first & head_of_second, "consecutive chunks must share overlap context"


def test_ref_formats_citation() -> None:
    chunk = Chunk(text="x", source="iom.pdf", locator="page 7", ordinal=0)
    assert chunk.ref == "iom.pdf — page 7"
