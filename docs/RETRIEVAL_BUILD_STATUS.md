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

This isolates the platform defect to the SentenceTransformer/PyTorch + FAISS process boundary. It is a runtime/platform defect, not a retrieval-performance signal.

## Frozen runtime policy — `retrieval-eval-v1.3`

The retrieval algorithm is unchanged. Only native-library process boundaries are changed.

The evaluator uses three isolated child processes:

1. **Query encoder worker** — imports Sentence Transformers/PyTorch, never FAISS; produces normalized query vectors with the frozen `all-MiniLM-L6-v2` model.
2. **FAISS worker** — imports FAISS, never PyTorch/Sentence Transformers; searches the frozen `IndexFlatIP` indexes using those query vectors.
3. **Reranker worker** — imports the frozen cross-encoder on CPU, never FAISS; reranks the exact E4 BM25+dense+RRF candidate sets.

The parent process handles only SQLite/BM25, chunk metadata, RRF assembly, metrics, and subprocess orchestration.

This does **not** change corpus membership, chunks, embedding model, normalized query vectors, FAISS search, BM25, candidate depth, RRF, reranker model, top-5 depth, locked questions, or metrics.

## Final frozen retrieval result

The complete `retrieval-eval-v1.3` artifact is accepted after post-evaluation plumbing validation.

### E0 — flat dense-only

- Recall@1/3/5: **0.0000 / 0.0000 / 0.0000**;
- MRR: **0.0000**;
- nDCG@5: **0.0000**;
- correct-source@1/@5: **0.0000 / 0.0000**;
- correct-source+page@1/@5: **0.0000 / 0.0000**.

### E4 — section-aware hybrid + reranker

- Recall@1: **0.2500**;
- Recall@3: **0.3636**;
- Recall@5: **0.4091**;
- MRR: **0.3106**;
- nDCG@5: **0.3353**;
- correct-source@1: **0.2727**;
- correct-source@5: **0.5000**;
- correct-source+page@1: **0.2500**;
- correct-source+page@5: **0.4091**;
- paired rank comparison: **E4 better 18 / E0 better 0 / ties 26**.

## Plumbing validation and branch attribution

`retrieval-plumbing-diagnostic-v1.0` was run after the frozen comparison solely to verify implementation correctness; it did not alter or rerun retrieval configuration.

Validation passed:

- E0 FAISS-row/chunk alignment: **20/20 exact top-1 self matches**;
- E4 FAISS-row/chunk alignment: **20/20 exact top-1 self matches**;
- fresh-vs-stored E0 embedding cosine: minimum **0.99999988**, mean **1.0**;
- fresh-vs-stored E4 embedding cosine: minimum **1.0**, mean **1.0**;
- all **8** benchmark target ADs are present in both E0 and E4 indexes.

Branch diagnostic at candidate depth 20:

- E0 dense correct source: **0/44 (0%)**;
- E0 dense correct source+page: **0/44 (0%)**;
- E4 dense correct source: **0/44 (0%)**;
- E4 dense correct source+page: **0/44 (0%)**;
- E4 BM25 correct source: **40/44 (90.9%)**, mean hit rank **2.625**;
- E4 BM25 correct source+page: **40/44 (90.9%)**, mean hit rank **3.1**.

All 44 answerable benchmark questions contain the target AD number literally. Therefore the accepted interpretation is:

1. the all-zero E0 result is **not** caused by FAISS/chunk misalignment or corrupted embeddings;
2. the frozen MiniLM dense branch does not retrieve the exact AD identifier successfully within top-20 on this benchmark, in either E0 or E4;
3. E4's gain is attributable primarily to the **hybrid lexical/section-aware architecture**, especially BM25 exact-term retrieval, not to superior dense retrieval;
4. the four BM25 source misses are **QA-039 to QA-042**, all in the conditional/multi-passage category;
5. BM25 has high candidate recall at depth 20, while the final E4 top-5 after fusion/reranking retains the correct page for only **18/44 (40.9%)**, so reranking/precision remains a limitation of the frozen system.

Benchmark composition must be reported as a limitation: the 44 answerable questions cover **8 distinct target ADs**, with **25/44** targeting AD `2006-0047`.

## Benchmark lock

The E0/E4 result is now final for the frozen retrieval experiment. Do not change chunking, model names, candidate depth, fusion, reranker, corpus membership, lifecycle policy, questions, or metrics based on these results.

Proceed to the hosted-LLM/full-QA stage using the frozen retrieval evidence and report retrieval-induced failures transparently; an LLM cannot recover evidence that retrieval failed to supply.
