"""API tests: TestClient, seeded ephemeral store, scripted gateway — offline."""

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from conftest import FakeEmbedder
from doc_qa.api.main import create_app
from doc_qa.chunking import Chunk
from doc_qa.store import VectorStore

DATASET = Path(__file__).resolve().parent.parent / "dataset"


class FakeGateway:
    def __init__(self, text: str) -> None:
        self.text = text

    def ask(self, prompt: str, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(text=self.text, provider="fake", model="fake")


def make_client(gateway_text: str, dataset_dir: Path = DATASET) -> TestClient:
    store = VectorStore(collection=f"api_{uuid4().hex}")
    embedder = FakeEmbedder()
    chunk = Chunk(
        text="AF-4520 wear ring clearance: 0.40-0.45 mm.",
        source="AF-4500_Series_IOM_Manual.pdf",
        locator="page 3",
        ordinal=0,
    )
    store.add([chunk], embedder.embed_texts([chunk.text]))
    app = create_app(
        dataset_dir=dataset_dir,
        store=store,
        embedder=embedder,
        gateway=FakeGateway(gateway_text),
        count_tokens=lambda t: len(t.split()),
    )
    return TestClient(app)


def test_query_returns_citation_with_page_deeplink() -> None:
    client = make_client('{"answer": "0.40-0.45 mm", "citations": [1]}')
    body = client.post("/query", json={"question": "clearance?"}).json()
    assert body["grounded"] is True
    assert body["citations"] == [
        {
            "source": "AF-4500_Series_IOM_Manual.pdf",
            "locator": "page 3",
            "href": "/documents/AF-4500_Series_IOM_Manual.pdf#page=3",
        }
    ]


def test_query_refusal_has_no_citations() -> None:
    client = make_client('{"answer": null, "citations": []}')
    body = client.post("/query", json={"question": "capital of France?"}).json()
    assert body["grounded"] is False
    assert body["citations"] == []


def test_documents_lists_the_corpus_with_hrefs() -> None:
    client = make_client("{}")
    docs = client.get("/documents").json()
    assert len(docs) == 12
    by_name = {d["name"]: d for d in docs}
    spec = by_name["AF-4500_Series_Spec_Sheet.csv"]
    assert spec["category"] == "specifications"
    assert spec["format"] == "CSV"
    assert spec["href"] == "/documents/AF-4500_Series_Spec_Sheet.csv"


def test_document_file_is_served_and_unknown_404s() -> None:
    client = make_client("{}")
    ok = client.get("/documents/AF-4500_Series_Spec_Sheet.csv")
    assert ok.status_code == 200
    assert b"AF-4510" in ok.content
    assert client.get("/documents/no_such_file.pdf").status_code == 404


def test_upload_indexes_supported_file(tmp_path: Path) -> None:
    client = make_client("{}", dataset_dir=tmp_path)
    response = client.post(
        "/upload", files={"file": ("memo.txt", b"Impeller torque memo: use 95 Nm.", "text/plain")}
    )
    assert response.status_code == 201
    assert response.json()["chunks_indexed"] == 1
    assert (tmp_path / "uploads" / "memo.txt").exists()


def test_upload_rejects_unsupported_format(tmp_path: Path) -> None:
    client = make_client("{}", dataset_dir=tmp_path)
    response = client.post("/upload", files={"file": ("book.epub", b"x", "application/epub")})
    assert response.status_code == 400
    assert not (tmp_path / "uploads" / "book.epub").exists(), "rejected files must not linger"
