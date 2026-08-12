"""Shared test doubles: deterministic, offline, no model downloads."""

from doc_qa.embeddings import Embedder


class FakeEmbedder(Embedder):
    """Deterministic 8-dim vectors from text content; no model, no network."""

    def __init__(self) -> None:
        super().__init__(model_name="fake")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float((hash(t) >> shift) % 97) / 97 for shift in range(8)] for t in texts]
