# RAG evaluation (end-to-end, live gateway, cached)

**Result: 16/18 correct — 88.9% (PASS, target ≥80%)** · Refusal probes: 3/3 refused · Zero-uncited-answers invariant: held

Embedding: BAAI/bge-small-en-v1.5, k=5. Correct = grounded ∧ citation-in-acceptable-set ∧ snippet-in-answer.

| Question | Grounded | Citation | Snippet | Correct | Provider |
|---|---|---|---|---|---|
| wear-ring-af4520 | ✅ | ✅ | ✅ | ✅ | groq |
| lubricant-flash-point | ✅ | ✅ | ✅ | ✅ | groq |
| warranty-14-months | ✅ | ✅ | ❌ | ❌ | groq |
| pump-screaming | ✅ | ✅ | ✅ | ✅ | groq |
| casing-bolt-torque | ✅ | ✅ | ✅ | ✅ | groq |
| max-wear-limit-af4530 | ✅ | ✅ | ✅ | ✅ | gemini-flash-lite |
| seal-service-interval | ✅ | ✅ | ✅ | ✅ | gemini-flash-lite |
| seal-replacement-tools | ✅ | ✅ | ✅ | ✅ | gemini-flash-lite |
| seal-safety-lockout | ✅ | ✅ | ❌ | ❌ | gemini-flash-lite |
| ah220-handling | ✅ | ✅ | ✅ | ✅ | gemini-flash-lite |
| pump-loses-prime | ✅ | ✅ | ✅ | ✅ | gemini-flash-lite |
| platinum-tier | ✅ | ✅ | ✅ | ✅ | gemini-flash-lite |
| pto-carryover | ✅ | ✅ | ✅ | ✅ | groq |
| total-backlog | ✅ | ✅ | ✅ | ✅ | groq |
| af4530-max-flow | ✅ | ✅ | ✅ | ✅ | groq |
| impeller-material-serial | ✅ | ✅ | ✅ | ✅ | groq |
| expense-approval | ✅ | ✅ | ✅ | ✅ | groq |
| emea-revenue | ✅ | ✅ | ✅ | ✅ | groq |

## Refusal probes (must refuse)

- ✅ What is the capital of France?
- ✅ What is the salary of Atlas's CEO?
- ✅ How do I configure a Cisco router?
