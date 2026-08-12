"""RAG core: retrieve → cited prompt → gateway → ENFORCED citations.

The citation contract is enforced in code, not requested in prose:

- The LLM never writes source names. It only selects context-block NUMBERS;
  provenance is resolved from retrieval metadata we attached in M2. A model
  can hallucinate a document title; it cannot hallucinate our metadata.
- An answer whose block numbers don't resolve is refused, not trusted.
- "Not in the documents" is a typed outcome (Answer.grounded=False), and the
  model is explicitly given that exit (answer: null) so it never has to invent.

No similarity floor in v1: unrelated queries still score ~0.4+ cosine on
small corpora, so a threshold would be a guess. The LLM's null-answer is the
refusal mechanism; a data-tuned floor is future work once the golden set grows.

All LLM traffic goes through the vendored llm_gateway (free tiers, failover).
"""

from __future__ import annotations

import json
from typing import Any, Protocol

from .embeddings import Embedder
from .models import Answer, Citation
from .store import RetrievedChunk, VectorStore

DEFAULT_K = 5
REFUSAL_TEXT = "This is not covered by the indexed documents."

SYSTEM_PROMPT = (
    "You are a technical assistant for Atlas Fluid Systems staff. "
    "Answer ONLY from the numbered context blocks provided. "
    'Reply with a single JSON object: {"answer": "<concise answer>", '
    '"citations": [<numbers of the blocks you used>]}. '
    'If the blocks do not contain the answer, reply exactly '
    '{"answer": null, "citations": []}. Never use outside knowledge.'
)


class SupportsAsk(Protocol):
    """Anything with the gateway's ask() shape (the real one, or a test fake)."""

    def ask(self, prompt: str, **kwargs: Any) -> Any: ...


class _GatewaySingleton:
    """Adapter over llm_gateway's module-level ask(); imported lazily."""

    def ask(self, prompt: str, **kwargs: Any) -> Any:
        import llm_gateway

        return llm_gateway.ask(prompt, **kwargs)


def _format_context(results: list[RetrievedChunk]) -> str:
    return "\n\n".join(
        f"[{n}] {r.chunk.ref}\n{r.chunk.text}" for n, r in enumerate(results, start=1)
    )


def _extract_json(text: str) -> dict | None:
    """Parse the outermost JSON object; tolerates code fences and prose around it."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _resolve_citations(raw: Any, results: list[RetrievedChunk]) -> list[Citation]:
    """Map the LLM's block numbers onto retrieval metadata; drop anything invalid."""
    citations: list[Citation] = []
    seen: set[tuple[str, str]] = set()
    for item in raw if isinstance(raw, list) else []:
        try:
            n = int(item)
        except (TypeError, ValueError):
            continue
        if not 1 <= n <= len(results):
            continue
        chunk = results[n - 1].chunk
        if (chunk.source, chunk.locator) not in seen:
            seen.add((chunk.source, chunk.locator))
            citations.append(Citation(source=chunk.source, locator=chunk.locator))
    return citations


def answer_question(
    question: str,
    store: VectorStore,
    embedder: Embedder,
    *,
    gateway: SupportsAsk | None = None,
    k: int = DEFAULT_K,
) -> Answer:
    """Answer from the corpus with enforced citations, or refuse."""
    results = store.query(embedder.embed_query(question), k=k)
    if not results:
        return Answer(text=REFUSAL_TEXT, grounded=False)

    gateway = gateway or _GatewaySingleton()
    prompt = f"Context blocks:\n\n{_format_context(results)}\n\nQuestion: {question}"
    response = gateway.ask(prompt, system=SYSTEM_PROMPT)
    provider = getattr(response, "provider", None)
    model = getattr(response, "model", None)

    def refusal() -> Answer:
        return Answer(text=REFUSAL_TEXT, grounded=False, provider=provider, model=model)

    payload = _extract_json(response.text)
    if payload is None:  # unparseable output is never trusted as an answer
        return refusal()
    text = payload.get("answer")
    if not isinstance(text, str) or not text.strip():
        return refusal()  # the model took its honest exit (answer: null)
    citations = _resolve_citations(payload.get("citations"), results)
    if not citations:  # grounded answers require at least one resolvable citation
        return refusal()
    return Answer(
        text=text.strip(), citations=citations, grounded=True, provider=provider, model=model
    )
