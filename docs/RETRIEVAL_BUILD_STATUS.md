# Retrieval Build Status

Last updated: 5 August 2026

This file records the frozen E0/E4 index-build state and retrieval-evaluation runtime provenance.

## Source gate

- Verified page source: `page-text-v1.1`.
- Strict Airbus-only development retrieval corpus: **1,786 PDFs / 6,002 pages**.
- Extraction failures: **0**.
- Unresolved weak/OCR pages: **0**.
- Five frozen unseen PDFs remain excluded.
- Dense model: `sentence-transformers/all-MiniLM-L6-v2`.
- Frozen research backends require sentence-transformers + FAISS; no hashing/numpy fallback is permitted.

## Frozen build

`rag-index-build-v1.2` is **ACCEPTED / FROZEN**.

Common configuration:

- document count: **1,786**;
- page source: `page-text-v1.1`;
- dense model: `sentence-transformers/all-MiniLM-L6-v2`;
- chunk count method: `whitespace_split`;
- sentence-transformers: **5.6.0**;
- FAISS CPU: **1.14.3**.

E0:

- **9,394** chunks;
- max chunk size **350**;
- FAISS `IndexFlatIP`;
- dense-only evaluation ranking.

E4:

- **12,634** chunks;
- max chunk size **450**;
- **2,924** multi-page chunks; max page span **5**;
- SQLite FTS5/BM25 + same dense model + FAISS + RRF;
- reranker `cross-encoder/ms-marco-MiniLM-L-6-v2`;
- candidate depth **20** per sparse/dense path.

Accepted index root:

```text
data_processed/indexes/rag_v1_2/
```

Older `rag_v1/` and `rag_v1_1/` workspaces remain audit history only.

## Retrieval evaluation runtime history

### Attempt 1 — runtime aborted

E0 processed all 44 answerable locked questions, then the process segfaulted at E4 question 1. No completed E4 measurement and no final comparison file were produced.

### Attempt 2 — runtime smoke aborted

The cross-encoder was pinned to CPU and a shared dense encoder was used. Model loading and reranker warm-up succeeded, but the process still segfaulted when the full E4 path executed in one process.

### Attempt 3 — candidate smoke aborted before reranking

The cross-encoder was moved to an isolated child process, but the parent still contained both SentenceTransformer/PyTorch and FAISS. The process segfaulted during the **E4 candidate smoke test immediately after the dense encoder loaded on MPS**, before the child reranker was invoked.

This isolates the remaining platform defect to the SentenceTransformer/PyTorch + FAISS process boundary. Upstream PyTorch macOS ARM reports document native OpenMP crashes when FAISS and PyTorch coexist in one process; Sentence Transformers has a corresponding FAISS compatibility report. This remains a runtime/platform defect, not a retrieval-performance signal.

## Frozen runtime policy — `retrieval-eval-v1.3`

The retrieval algorithm is unchanged. Only native-library process boundaries are changed.

The evaluator now uses three isolated child processes:

1. **Query encoder worker** — imports Sentence Transformers/PyTorch, never FAISS; produces normalized query vectors with the frozen `all-MiniLM-L6-v2` model.
2. **FAISS worker** — imports FAISS, never PyTorch/Sentence Transformers; searches the frozen `IndexFlatIP` indexes using those query vectors.
3. **Reranker worker** — imports the frozen cross-encoder on CPU, never FAISS; reranks the exact E4 BM25+dense+RRF candidate sets.

The parent process handles only SQLite/BM25, chunk metadata, RRF assembly, metrics, and subprocess orchestration. It does not instantiate SentenceTransformer, CrossEncoder, or FAISS.

This does **not** change:

- corpus membership;
- E0/E4 chunks;
- embedding model;
- normalized query-vector semantics;
- FAISS `IndexFlatIP` search;
- BM25 retrieval;
- candidate depth (**20**);
- RRF policy/constant;
- reranker model;
- top-5 depth;
- locked questions; or
- metric definitions.

A fully isolated non-benchmark E4 smoke query must pass query encoding → FAISS search → BM25/RRF assembly → isolated CPU reranking before the 44 locked questions are loaded.

## Benchmark lock

The E0/E4 configuration remains frozen. Do not change chunking, model names, candidate depth, fusion, corpus membership, lifecycle policy, questions, or metrics based on any locked result. Runtime-only fixes are allowed only when independent of retrieval performance and must remain documented.
