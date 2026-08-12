# Embedding bake-off — M3

Corpus: 6 PDFs. Questions: 12 (golden set entries with a loader as of M3).
Chunking: 500 tokens / 50 overlap, using **each candidate's own tokenizer**.
Retrieval: cosine top-5, isolated Chroma collection per candidate. CPU only.

| Model | Chunks | doc-hit@1 | doc-hit@3 | page-hit@3 | median ms | p95 ms | ingest s |
|---|---|---|---|---|---|---|---|
| sentence-transformers/all-MiniLM-L6-v2 | 12 | 42% | 92% | 83% | 14.6 | 18.3 | 7.0 |
| BAAI/bge-small-en-v1.5 **← winner** | 12 | 83% | 100% | 92% | 13.8 | 15.7 | 7.0 |

**Winner: `BAAI/bge-small-en-v1.5`** (rule: page-hit@3, then doc-hit@3, then median latency). Latency target ≤100ms: met (median 13.8ms).

## Per-question results (doc@1 / doc@3 / page@3)

| Question | all-MiniLM-L6-v2 | bge-small-en-v1.5 |
|---|---|---|
| wear-ring-af4520 | ✅✅✅ | ✅✅✅ |
| lubricant-flash-point | ❌✅✅ | ❌✅❌ |
| warranty-14-months | ❌❌❌ | ✅✅✅ |
| pump-screaming | ❌✅✅ | ✅✅✅ |
| casing-bolt-torque | ❌✅✅ | ✅✅✅ |
| max-wear-limit-af4530 | ✅✅✅ | ✅✅✅ |
| seal-service-interval | ✅✅❌ | ❌✅✅ |
| seal-replacement-tools | ✅✅✅ | ✅✅✅ |
| seal-safety-lockout | ✅✅✅ | ✅✅✅ |
| ah220-handling | ❌✅✅ | ✅✅✅ |
| pump-loses-prime | ❌✅✅ | ✅✅✅ |
| platinum-tier | ❌✅✅ | ✅✅✅ |
