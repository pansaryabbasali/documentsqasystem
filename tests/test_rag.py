"""RAG core tests: scripted gateway fakes, seeded store, fully offline.

Every path that could produce an ungrounded answer must end in a refusal —
that's the pilot's hard criterion, so it gets the densest test coverage.
"""

from types import SimpleNamespace
from uuid import uuid4

from conftest import FakeEmbedder
from doc_qa.chunking import Chunk
from doc_qa.rag import REFUSAL_TEXT, answer_question
from doc_qa.store import VectorStore


class FakeGateway:
    """Returns a scripted response; records the prompt it was asked."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.prompts: list[str] = []

    def ask(self, prompt: str, **kwargs: object) -> SimpleNamespace:
        self.prompts.append(prompt)
        return SimpleNamespace(text=self.text, provider="fake-provider", model="fake-model")


class ExplodingGateway:
    def ask(self, prompt: str, **kwargs: object) -> SimpleNamespace:
        raise AssertionError("gateway must not be called")


def seeded_store() -> VectorStore:
    store = VectorStore(collection=f"rag_{uuid4().hex}")
    chunks = [
        Chunk(text="Wear ring clearance AF-4520: 0.40-0.45 mm.", source="iom.pdf",
              locator="page 3", ordinal=0),
        Chunk(text="Warranty: 24 months from commissioning.", source="warranty.pdf",
              locator="page 1", ordinal=0),
    ]
    store.add(chunks, FakeEmbedder().embed_texts([c.text for c in chunks]))
    return store


def ask(gateway_text: str) -> tuple:
    gateway = FakeGateway(gateway_text)
    answer = answer_question("clearance?", seeded_store(), FakeEmbedder(), gateway=gateway)
    return answer, gateway


def test_grounded_answer_resolves_citations_from_metadata() -> None:
    answer, gateway = ask('{"answer": "0.40-0.45 mm", "citations": [1, 2]}')
    assert answer.grounded
    assert answer.text == "0.40-0.45 mm"
    assert {(c.source, c.locator) for c in answer.citations} == {
        ("iom.pdf", "page 3"),
        ("warranty.pdf", "page 1"),
    }
    assert answer.provider == "fake-provider"
    assert "[1]" in gateway.prompts[0] and "clearance?" in gateway.prompts[0]


def test_fenced_json_is_parsed() -> None:
    answer, _ = ask('```json\n{"answer": "0.40-0.45 mm", "citations": [1]}\n```')
    assert answer.grounded


def test_null_answer_becomes_refusal() -> None:
    answer, _ = ask('{"answer": null, "citations": []}')
    assert not answer.grounded
    assert answer.text == REFUSAL_TEXT
    assert answer.citations == []


def test_malformed_output_becomes_refusal() -> None:
    answer, _ = ask("The clearance is 0.40-0.45 mm (IOM manual).")  # prose, no JSON
    assert not answer.grounded


def test_invalid_citation_indices_are_dropped_and_all_invalid_refuses() -> None:
    answer, _ = ask('{"answer": "0.40-0.45 mm", "citations": [99, 0, "x"]}')
    assert not answer.grounded, "an answer with no resolvable citation must refuse"


def test_string_indices_and_duplicates_are_normalized() -> None:
    answer, _ = ask('{"answer": "0.40-0.45 mm", "citations": ["1", 1, 1]}')
    assert answer.grounded
    assert len(answer.citations) == 1


def test_empty_store_refuses_without_calling_gateway() -> None:
    empty = VectorStore(collection=f"rag_{uuid4().hex}")
    answer = answer_question("anything?", empty, FakeEmbedder(), gateway=ExplodingGateway())
    assert not answer.grounded
