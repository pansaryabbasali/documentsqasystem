"""Embedder tests.

The construction/prefix tests are offline. The behavioral test downloads a
real model (~90MB, cached after first run) and is opt-in via the `models`
marker: pytest -m models
"""

import pytest

from doc_qa.embeddings import Embedder


def test_construction_is_lazy_no_model_load() -> None:
    embedder = Embedder("this-model/does-not-exist")
    assert embedder._model is None  # nothing downloaded, nothing imported


@pytest.mark.models
def test_token_counter_sees_raw_lengths_not_padded() -> None:
    """Regression: MiniLM's tokenizer.json pads to 128 — every count was 128."""
    from doc_qa.tokenization import get_token_counter

    for model in ("sentence-transformers/all-MiniLM-L6-v2", "BAAI/bge-small-en-v1.5"):
        count = get_token_counter(model)
        assert count("") == 0, f"{model}: empty text must count 0"
        assert count("pump") < count("pump impeller wear ring clearance"), model


@pytest.mark.models
def test_embeddings_are_normalized_and_semantically_ordered() -> None:
    embedder = Embedder()  # default model
    vectors = embedder.embed_texts(
        [
            "Replace the mechanical seal on the pump.",
            "Procedure for changing a pump's mechanical seal.",
            "Employees receive 25 days of annual leave.",
        ]
    )
    assert all(abs(sum(x * x for x in v) - 1.0) < 1e-3 for v in vectors), "unit norm"

    def dot(a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b, strict=True))

    seal_pair = dot(vectors[0], vectors[1])
    seal_vs_leave = dot(vectors[0], vectors[2])
    assert seal_pair > seal_vs_leave, "paraphrases must be closer than unrelated text"

    query = embedder.embed_query("how do I replace a mechanical seal")
    assert len(query) == len(vectors[0])
