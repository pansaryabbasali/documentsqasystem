"""doc-qa console commands (typer), mirroring the vendored gateway's CLI style."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from .embeddings import DEFAULT_EMBEDDING_MODEL, Embedder
from .ingest import ingest_directory
from .store import VectorStore
from .tokenization import get_token_counter

app = typer.Typer(help="Atlas Document Q&A", no_args_is_help=True)
console = Console()


@app.command()
def ingest(
    dataset: Annotated[
        Path, typer.Argument(help="Directory of documents to index")
    ] = Path("dataset"),
    db: Annotated[
        Path, typer.Option(help="Vector store directory (created if missing)")
    ] = Path(".chroma"),
    model: Annotated[str, typer.Option(help="Local embedding model")] = DEFAULT_EMBEDDING_MODEL,
) -> None:
    """Index all supported documents under DATASET into the local vector store."""
    store = VectorStore(path=db)
    stats = ingest_directory(
        dataset, store, Embedder(model), count_tokens=get_token_counter(model)
    )
    console.print(
        f"[green]Indexed[/green] {stats.files_indexed} files "
        f"→ {stats.chunks_indexed} chunks → {db}/ (model: {model})"
    )
    if stats.skipped:
        console.print(f"[yellow]Skipped (no loader yet):[/yellow] {', '.join(stats.skipped)}")
