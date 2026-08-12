"""Local embedding models via sentence-transformers. No API calls, no cost.

The default model is a placeholder until the M3 bake-off
(eval/embedding_bakeoff.py) picks the winner on measured retrieval quality;
the constant below is updated by that decision and the report records why.

Some models are trained with an instruction prefix on *queries* (not on the
indexed passages) — bge's retrieval quality drops measurably without it. The
prefix lives in a per-model table here so callers never need to know.
"""

from __future__ import annotations

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

_QUERY_PREFIXES = {
    "BAAI/bge-small-en-v1.5": "Represent this sentence for searching relevant passages: ",
}


class Embedder:
    """Wraps one sentence-transformers model; loads it lazily on first use."""

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        self.model_name = model_name
        self._model = None  # loaded on first embed call, not at construction

    @property
    def model(self):  # lazy: importing torch takes seconds; only pay when embedding
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed passages for indexing. Unit-normalized so cosine ≡ dot product."""
        return self.model.encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        """Embed a search query, applying the model's query prefix if it has one."""
        prefix = _QUERY_PREFIXES.get(self.model_name, "")
        return self.embed_texts([prefix + text])[0]
