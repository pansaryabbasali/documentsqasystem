"""M4 RAG evaluation: end-to-end answer quality against the golden set.

A question is CORRECT when all three hold:
  1. grounded (the system answered rather than refused)
  2. citation-correct: at least one cited (document, page) is in the
     question's acceptable set — the pilot's citation criterion
  3. answer-correct: the normalized answer contains the golden snippet

Also runs out-of-corpus refusal probes (must refuse — the model certainly
"knows" these answers, which is exactly the point) and asserts the zero-
uncited-answers invariant on every grounded answer.

Gateway responses are cached in eval/.rag_cache.json (gitignored) keyed by
(embedding model, question, k) so re-runs don't burn free-tier quota.

Target: >=80% correct on the active golden questions.
Run:  python eval/rag_eval.py    (writes eval/rag_eval_M4.md; exit 1 if below)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from uuid import uuid4

from embedding_bakeoff import acceptable, supported_today
from extraction_eval import normalize

from doc_qa.embeddings import DEFAULT_EMBEDDING_MODEL, Embedder
from doc_qa.ingest import ingest_directory
from doc_qa.models import Answer
from doc_qa.rag import DEFAULT_K, answer_question
from doc_qa.store import VectorStore
from doc_qa.tokenization import get_token_counter

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "eval" / "rag_eval.md"
CACHE_PATH = ROOT / "eval" / ".rag_cache.json"
TARGET_PERCENT = 80.0

REFUSAL_PROBES = [
    "What is the capital of France?",
    "What is the salary of Atlas's CEO?",
    "How do I configure a Cisco router?",
]


def cached_answer(question: str, store: VectorStore, embedder: Embedder, cache: dict) -> Answer:
    key = f"{DEFAULT_EMBEDDING_MODEL}|k={DEFAULT_K}|{question}"
    if key not in cache:
        answer = answer_question(question, store, embedder)
        cache[key] = answer.model_dump()
        CACHE_PATH.write_text(json.dumps(cache, indent=2))
    return Answer.model_validate(cache[key])


def main() -> int:
    golden = json.loads((ROOT / "eval" / "golden_questions.json").read_text())
    questions = [q for q in golden if supported_today(q)]
    cache = json.loads(CACHE_PATH.read_text()) if CACHE_PATH.exists() else {}

    embedder = Embedder()
    store = VectorStore(collection=f"rag_eval_{uuid4().hex}")
    ingest_directory(ROOT / "dataset", store, embedder,
                     count_tokens=get_token_counter(DEFAULT_EMBEDDING_MODEL))

    rows, correct = [], 0
    for q in questions:
        answer = cached_answer(q["question"], store, embedder, cache)
        assert not (answer.grounded and not answer.citations), "uncited grounded answer"
        cite_ok = answer.grounded and any(
            acceptable(q, c.source, c.locator, pages_matter=True) for c in answer.citations
        )
        # digit-boundary match: "5" must not ride inside "25"/"150", but "312"
        # still matches "312M" and "annual" still matches "annually" (full
        # word-boundary \b proved too strict — it failed both of those).
        snippet = normalize(q["answer_snippet"])
        snip_ok = bool(snippet) and bool(
            re.search(rf"(?<!\d){re.escape(snippet)}(?!\d)", normalize(answer.text))
        )
        ok = answer.grounded and cite_ok and snip_ok
        correct += ok
        rows.append((q["id"], answer, cite_ok, snip_ok, ok))

    refusals = []
    for probe in REFUSAL_PROBES:
        answer = cached_answer(probe, store, embedder, cache)
        assert not (answer.grounded and not answer.citations), "uncited grounded answer"
        refusals.append((probe, not answer.grounded))
    refused = sum(ok for _, ok in refusals)

    rate = 100 * correct / len(rows)
    verdict = "PASS" if rate >= TARGET_PERCENT else "FAIL"
    check = lambda b: "✅" if b else "❌"  # noqa: E731
    lines = [
        "# RAG evaluation (end-to-end, live gateway, cached)",
        "",
        f"**Result: {correct}/{len(rows)} correct — {rate:.1f}% ({verdict}, "
        f"target ≥{TARGET_PERCENT:.0f}%)** · Refusal probes: {refused}/{len(refusals)} refused"
        " · Zero-uncited-answers invariant: held",
        "",
        f"Embedding: {DEFAULT_EMBEDDING_MODEL}, k={DEFAULT_K}. Correct = grounded ∧ "
        "citation-in-acceptable-set ∧ snippet-in-answer.",
        "",
        "| Question | Grounded | Citation | Snippet | Correct | Provider |",
        "|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {qid} | {check(a.grounded)} | {check(c)} | {check(s)} | {check(ok)} "
        f"| {a.provider or '—'} |"
        for qid, a, c, s, ok in rows
    ]
    lines += ["", "## Refusal probes (must refuse)", ""]
    lines += [f"- {check(ok)} {probe}" for probe, ok in refusals]
    REPORT.write_text("\n".join(lines) + "\n")
    print(f"{correct}/{len(rows)} = {rate:.1f}% [{verdict}] · refusals {refused}/"
          f"{len(refusals)} → {REPORT.relative_to(ROOT)}")
    return 0 if rate >= TARGET_PERCENT and refused == len(refusals) else 1


if __name__ == "__main__":
    sys.exit(main())
