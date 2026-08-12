"""HTTP API: query with citations, document library, file serving, upload.

Built as an app FACTORY (create_app) so tests inject a seeded store, a fake
embedder, and a scripted gateway; the module-level ``app`` at the bottom is
the production wiring that ``uvicorn doc_qa.api.main:app`` serves.

Citation hrefs are computed here (not in the RAG core): the core knows
provenance, only the API knows URLs. PDF citations deep-link to the page
(``#page=N`` is honored by browser PDF viewers) — precise citations beat
bare file links.
"""

from __future__ import annotations

import re
import shutil
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from doc_qa.embeddings import Embedder
from doc_qa.errors import UnsupportedFormatError
from doc_qa.ingest import ingest_file
from doc_qa.models import Answer
from doc_qa.rag import DEFAULT_K, SupportsAsk, answer_question
from doc_qa.store import VectorStore

_PAGE_LOCATOR = re.compile(r"^page (\d+)$")


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    k: int = Field(default=DEFAULT_K, ge=1, le=20)


class CitationOut(BaseModel):
    source: str
    locator: str
    href: str  # link straight to the document (PDFs: to the exact page)


class QueryResponse(BaseModel):
    text: str
    grounded: bool
    citations: list[CitationOut]
    provider: str | None
    model: str | None


class DocumentOut(BaseModel):
    name: str
    category: str  # dataset subdirectory, e.g. "product_manuals"
    format: str  # upper-case suffix, e.g. "PDF"
    href: str


def _citation_href(source: str, locator: str) -> str:
    href = f"/documents/{source}"
    match = _PAGE_LOCATOR.match(locator)
    return f"{href}#page={match.group(1)}" if match else href


def create_app(
    *,
    dataset_dir: Path,
    store: VectorStore,
    embedder: Embedder,
    gateway: SupportsAsk | None = None,
    count_tokens: Callable[[str], int] | None = None,
) -> FastAPI:
    app = FastAPI(title="Atlas Document Q&A", version="0.1.0")
    dataset_dir = Path(dataset_dir)

    def document_index() -> dict[str, Path]:
        """name -> path for every corpus file. Lookup by exact indexed name
        (never by request-supplied path) is also the path-traversal guard."""
        return {p.name: p for p in sorted(dataset_dir.rglob("*")) if p.is_file()}

    @app.post("/query", response_model=QueryResponse)
    def query(request: QueryRequest) -> QueryResponse:
        answer: Answer = answer_question(
            request.question, store, embedder, gateway=gateway, k=request.k
        )
        return QueryResponse(
            text=answer.text,
            grounded=answer.grounded,
            citations=[
                CitationOut(
                    source=c.source, locator=c.locator, href=_citation_href(c.source, c.locator)
                )
                for c in answer.citations
            ],
            provider=answer.provider,
            model=answer.model,
        )

    @app.get("/documents", response_model=list[DocumentOut])
    def documents() -> list[DocumentOut]:
        return [
            DocumentOut(
                name=path.name,
                category=path.parent.name,
                format=path.suffix.lstrip(".").upper(),
                href=f"/documents/{path.name}",
            )
            for path in document_index().values()
        ]

    @app.get("/documents/{name}")
    def document(name: str) -> FileResponse:
        path = document_index().get(name)
        if path is None:
            raise HTTPException(status_code=404, detail=f"no such document: {name}")
        return FileResponse(path, filename=path.name)

    @app.post("/upload", status_code=201)
    def upload(file: UploadFile) -> dict[str, int | str]:
        if not file.filename:
            raise HTTPException(status_code=400, detail="upload has no filename")
        destination = dataset_dir / "uploads" / Path(file.filename).name
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as target:
            shutil.copyfileobj(file.file, target)
        try:
            counter = count_tokens or _default_token_counter()
            chunks = ingest_file(destination, store, embedder, count_tokens=counter)
        except UnsupportedFormatError as exc:
            destination.unlink()  # don't keep files we can't index
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"name": destination.name, "chunks_indexed": chunks}

    return app


def _default_token_counter() -> Callable[[str], int]:
    from doc_qa.tokenization import get_token_counter

    return get_token_counter()


# Production wiring: uvicorn doc_qa.api.main:app  (run from the repo root)
app = create_app(
    dataset_dir=Path("dataset"),
    store=VectorStore(path=Path(".chroma")),
    embedder=Embedder(),
)
