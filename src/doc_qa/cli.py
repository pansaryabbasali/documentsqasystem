"""doc-qa console commands (typer), mirroring the vendored gateway's CLI style."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from .embeddings import DEFAULT_EMBEDDING_MODEL, Embedder
from .ingest import ingest_directory
from .rag import DEFAULT_K, answer_question
from .store import VectorStore
from .tokenization import get_token_counter

app = typer.Typer(help="Atlas Document Q&A", no_args_is_help=True)
console = Console()


@app.callback()
def main() -> None:
    """Atlas Document Q&A.

    Typer collapses a single-command app into that command, which would make
    ``doc-qa ingest`` parse "ingest" as the dataset argument. An explicit
    callback keeps commands as subcommands until more are added (M4: ask).
    """


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


@app.command()
def ask(
    question: Annotated[str, typer.Argument(help="Natural-language question")],
    db: Annotated[Path, typer.Option(help="Vector store directory")] = Path(".chroma"),
    model: Annotated[str, typer.Option(help="Local embedding model")] = DEFAULT_EMBEDDING_MODEL,
    k: Annotated[int, typer.Option(help="Context chunks to retrieve")] = DEFAULT_K,
) -> None:
    """Answer QUESTION from the indexed corpus, with citations — or refuse."""
    store = VectorStore(path=db)
    if store.count() == 0:
        console.print(f"[red]Vector store at {db}/ is empty — run 'doc-qa ingest' first.[/red]")
        raise typer.Exit(code=1)
    answer = answer_question(question, store, Embedder(model), k=k)
    style = "green" if answer.grounded else "yellow"
    console.print(f"[{style}]{answer.text}[/{style}]")
    for citation in answer.citations:
        console.print(f"  [dim]source:[/dim] {citation.ref}")
    if answer.provider:
        console.print(f"[dim]served by {answer.provider}/{answer.model}[/dim]")
