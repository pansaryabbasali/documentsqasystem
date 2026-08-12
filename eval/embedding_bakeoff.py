"""M3 embedding bake-off: choose the default local embedding model with data.

Method: for each candidate, ingest the corpus into an isolated collection —
chunked with that model's OWN tokenizer — then run every golden question whose
primary source has a loader today, and measure:

- doc-hit@1 / doc-hit@3: an acceptable source document in the top 1 / top 3
- page-hit@3: an acceptable (document, page) in the top 3 — the citation metric
- query latency (embed + search), median and p95, on CPU

Winner: highest page-hit@3; ties broken by doc-hit@3, then median latency.
The result is written to eval/embedding_bakeoff.md and DEFAULT_EMBEDDING_MODEL
in doc_qa/embeddings.py is set to the winner.

Run:  python eval/embedding_bakeoff.py
"""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from uuid import uuid4

from doc_qa.embeddings import Embedder
from doc_qa.errors import UnsupportedFormatError
from doc_qa.ingest import ingest_directory
from doc_qa.loaders import loader_for
from doc_qa.store import VectorStore
from doc_qa.tokenization import get_token_counter

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "eval" / "embedding_bakeoff.md"
CANDIDATES = ["sentence-transformers/all-MiniLM-L6-v2", "BAAI/bge-small-en-v1.5"]
K = 5
LATENCY_TARGET_MS = 100.0


def supported_today(question: dict) -> bool:
    try:
        loader_for(ROOT / "dataset" / question["sources"][0]["file"])
        return True
    except UnsupportedFormatError:
        return False


def acceptable(question: dict, source: str, locator: str, *, pages_matter: bool) -> bool:
    for s in question["sources"]:
        if source == Path(s["file"]).name and (
            not pages_matter or not s["pages"] or locator in s["pages"]
        ):
            return True
    return False


def evaluate(model_name: str, questions: list[dict]) -> dict:
    embedder = Embedder(model_name)
    store = VectorStore(collection=f"bakeoff_{uuid4().hex}")
    t_ingest = time.perf_counter()
    stats = ingest_directory(
        ROOT / "dataset", store, embedder, count_tokens=get_token_counter(model_name)
    )
    ingest_seconds = time.perf_counter() - t_ingest

    doc1 = doc3 = page3 = 0
    latencies_ms: list[float] = []
    per_question: list[tuple[str, bool, bool, bool]] = []
    for q in questions:
        t0 = time.perf_counter()
        results = store.query(embedder.embed_query(q["question"]), k=K)
        latencies_ms.append((time.perf_counter() - t0) * 1000)
        top3 = results[:3]
        d1 = acceptable(q, top3[0].chunk.source, top3[0].chunk.locator, pages_matter=False)
        d3 = any(acceptable(q, r.chunk.source, r.chunk.locator, pages_matter=False) for r in top3)
        p3 = any(acceptable(q, r.chunk.source, r.chunk.locator, pages_matter=True) for r in top3)
        doc1 += d1
        doc3 += d3
        page3 += p3
        per_question.append((q["id"], d1, d3, p3))

    n = len(questions)
    return {
        "model": model_name,
        "chunks": stats.chunks_indexed,
        "ingest_seconds": ingest_seconds,
        "doc1": 100 * doc1 / n,
        "doc3": 100 * doc3 / n,
        "page3": 100 * page3 / n,
        "median_ms": statistics.median(latencies_ms),
        "p95_ms": sorted(latencies_ms)[max(0, round(0.95 * len(latencies_ms)) - 1)],
        "per_question": per_question,
    }


def main() -> None:
    golden = json.loads((ROOT / "eval" / "golden_questions.json").read_text())
    questions = [q for q in golden if supported_today(q)]
    print(f"{len(questions)} golden questions active (PDF corpus)")
    results = [evaluate(m, questions) for m in CANDIDATES]
    winner = max(results, key=lambda r: (r["page3"], r["doc3"], -r["median_ms"]))

    check = lambda ok: "✅" if ok else "❌"  # noqa: E731
    lines = [
        "# Embedding bake-off — M3",
        "",
        f"Corpus: 6 PDFs. Questions: {len(questions)} (golden set entries with a loader as of M3).",
        "Chunking: 500 tokens / 50 overlap, using **each candidate's own tokenizer**.",
        "Retrieval: cosine top-5, isolated Chroma collection per candidate. CPU only.",
        "",
        "| Model | Chunks | doc-hit@1 | doc-hit@3 | page-hit@3 | median ms | p95 ms | ingest s |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        mark = " **← winner**" if r is winner else ""
        lines.append(
            f"| {r['model']}{mark} | {r['chunks']} | {r['doc1']:.0f}% | {r['doc3']:.0f}% "
            f"| {r['page3']:.0f}% | {r['median_ms']:.1f} | {r['p95_ms']:.1f} "
            f"| {r['ingest_seconds']:.1f} |"
        )
    lines += [
        "",
        f"**Winner: `{winner['model']}`** (rule: page-hit@3, then doc-hit@3, then median "
        f"latency). Latency target ≤{LATENCY_TARGET_MS:.0f}ms: "
        f"{'met' if winner['median_ms'] <= LATENCY_TARGET_MS else 'MISSED'} "
        f"(median {winner['median_ms']:.1f}ms).",
        "",
        "## Per-question results (doc@1 / doc@3 / page@3)",
        "",
        "| Question | " + " | ".join(r["model"].split("/")[-1] for r in results) + " |",
        "|---|" + "---|" * len(results),
    ]
    for i, (qid, *_rest) in enumerate(results[0]["per_question"]):
        cells = [
            f"{check(r['per_question'][i][1])}{check(r['per_question'][i][2])}{check(r['per_question'][i][3])}"
            for r in results
        ]
        lines.append(f"| {qid} | " + " | ".join(cells) + " |")
    REPORT.write_text("\n".join(lines) + "\n")
    print(f"winner: {winner['model']}  (page-hit@3 {winner['page3']:.0f}%, "
          f"median {winner['median_ms']:.1f}ms) → {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
