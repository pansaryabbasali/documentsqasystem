"""Local vector store on ChromaDB: cosine retrieval with provenance intact.

Every stored chunk keeps its source + locator as metadata, so retrieval
returns citable results — the RAG layer never has to guess where text came
from. Telemetry is disabled (offline-by-default is a project rule).

Caveat discovered in testing: Chroma's "ephemeral" client is NOT isolated —
one in-process system is shared per settings, so two VectorStore() instances
with the same collection name see each other's data. Callers needing
isolation (tests, the bake-off) must pass distinct ``collection`` names.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb.config import Settings

from .chunking import Chunk

DEFAULT_COLLECTION = "atlas_docs"


@dataclass(frozen=True)
class RetrievedChunk:
    """A chunk plus its retrieval similarity (cosine, 1.0 = identical)."""

    chunk: Chunk
    score: float


class VectorStore:
    """One Chroma collection: persistent when given a path, in-memory otherwise."""

    def __init__(
        self, path: Path | str | None = None, collection: str = DEFAULT_COLLECTION
    ) -> None:
        settings = Settings(anonymized_telemetry=False)
        self._client = (
            chromadb.PersistentClient(path=str(path), settings=settings)
            if path
            else chromadb.EphemeralClient(settings=settings)
        )
        self._collection = self._client.get_or_create_collection(
            collection, metadata={"hnsw:space": "cosine"}
        )

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        """Store chunks; idempotent — re-ingesting the same chunk updates in place."""
        if len(chunks) != len(embeddings):
            raise ValueError(f"{len(chunks)} chunks but {len(embeddings)} embeddings")
        if not chunks:
            return
        self._collection.upsert(
            ids=[f"{c.source}|{c.locator}|{c.ordinal}" for c in chunks],
            embeddings=embeddings,
            documents=[c.text for c in chunks],
            metadatas=[
                {"source": c.source, "locator": c.locator, "ordinal": c.ordinal} for c in chunks
            ],
        )

    def query(self, embedding: list[float], k: int = 5) -> list[RetrievedChunk]:
        """Top-k most similar chunks, best first. Cosine distance → score = 1 - d."""
        k = min(k, self.count())
        if k == 0:
            return []
        result = self._collection.query(query_embeddings=[embedding], n_results=k)
        retrieved = []
        for text, meta, distance in zip(
            result["documents"][0], result["metadatas"][0], result["distances"][0], strict=True
        ):
            chunk = Chunk(
                text=text,
                source=str(meta["source"]),
                locator=str(meta["locator"]),
                ordinal=int(meta["ordinal"]),
            )
            retrieved.append(RetrievedChunk(chunk=chunk, score=1.0 - distance))
        return retrieved

    def count(self) -> int:
        return self._collection.count()
