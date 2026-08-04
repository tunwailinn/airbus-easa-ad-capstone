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

## Build history

### `rag-index-build-v1.0` — rejected before benchmark

The first infrastructure build completed, but its report mixed a lexical counter with whitespace-based construction limits. Reported maxima were therefore inconsistent with the declared chunk policy. No locked retrieval scores were opened.

### `rag-index-build-v1.1` — partial, not benchmark-eligible

E0 built successfully over all 1,786 documents, but E4 stopped before embedding/index construction because the strict gate found a **476**-unit section chunk against the frozen **450** maximum. Root cause: legacy E4 construction counted blocks with `TOKEN_RE.findall(...)` while the frozen limit/report used whitespace-delimited units.

No E4 v1.1 index was accepted and no locked benchmark scores were opened.

### `rag-index-build-v1.2` — ACCEPTED / FROZEN

The reviewed `build_summary.json` passes all pre-benchmark gates.

Common configuration:

- retrieval build version: **`rag-index-build-v1.2`**;
- page source: **`page-text-v1.1`**;
- document count: **1,786**;
- dense model: `sentence-transformers/all-MiniLM-L6-v2`;
- chunk-size policy: `whitespace_split`;
- sentence-transformers: **5.6.0**;
- FAISS CPU: **1.14.3**.

E0 accepted build:

- experiment: `E0-flat-dense`;
- chunks: **9,394**;
- documents: **1,786**;
- max chunk size: **350**;
- multi-page chunks: **0**;
- dense backend: `sentence_transformers`;
- dense index: `faiss_index_flat_ip`.

E4 accepted build:

- experiment: `E4-section-hybrid`;
- chunks: **12,634**;
- documents: **1,786**;
- max chunk size: **450**;
- multi-page chunks: **2,924**;
- max page span: **5**;
- dense backend: `sentence_transformers`;
- dense index: `faiss_index_flat_ip`;
- sparse backend: `sqlite_fts5_bm25`;
- fusion: `reciprocal_rank_fusion`;
- reranker model: `cross-encoder/ms-marco-MiniLM-L-6-v2`.

The E0 artifact was reused from the valid v1.1 E0 build and revalidated in the v1.2 workspace. E4 was rebuilt with corrected whitespace-based construction accounting.

## Frozen evaluation workspace

Accepted index root:

```text
data_processed/indexes/rag_v1_2/
├── e0_flat_dense/
├── e4_section_hybrid/
└── build_summary.json
```

Keep older workspaces for audit history:

```text
data_processed/indexes/rag_v1/
data_processed/indexes/rag_v1_1/
```

They are not valid inputs to the final retrieval evaluator.

## Retrieval evaluation runtime history

### First execution attempt — runtime aborted, no completed E4 measurement

The accepted v1.2 indexes were used. E0 processed all 44 answerable locked retrieval questions, but before aggregate results were written the process terminated with a native macOS segmentation fault at E4 question 1 while another copy of the dense sentence-transformer was being loaded. The final `retrieval_comparison.json` was not produced and no completed E4 score was observed.

This was treated as a runtime defect, not a retrieval-performance signal. No chunking, model, candidate-depth, fusion, reranker, corpus-membership, lifecycle, or question changes were made.

### Frozen runtime policy — `retrieval-eval-v1.1`

The rerun uses the same accepted v1.2 indexes and frozen ranking logic with only these runtime-stability controls:

- one shared `DenseEncoder` instance is attached to both E0 and E4, preventing a duplicate `all-MiniLM-L6-v2` model load between systems;
- the shared dense query encoder retains Sentence Transformers' normal single-device auto-selection so dense retrieval remains on the same model/runtime family used by the build;
- the cross-encoder reranker is explicitly pinned to **CPU** to avoid simultaneous dense-model and reranker residency on Apple MPS;
- no multiprocessing pool is requested;
- the output report records the actual dense query device, CPU reranker device, and shared-encoder policy;
- progress heartbeats cover dense-model and reranker loading as well as question-by-question evaluation.

These controls are runtime/reproducibility choices only. They do not change retrieval architecture or frozen benchmark configuration.

## Benchmark lock

The E0/E4 retrieval configuration remains frozen. From this point onward:

1. do not change chunking, embedding model, candidate depth, RRF policy, reranker model, corpus membership, lifecycle rules, or locked questions based on retrieval results;
2. rerun the locked retrieval evaluation from the beginning using `retrieval-eval-v1.1` and report the completed results as observed;
3. implementation/runtime defects may be fixed only when independent of retrieval performance and must be documented explicitly.

The evaluator is locked to `rag-index-build-v1.2`, validates the 1,786-document and 350/450 build gates before evaluation, shares one dense query encoder across E0/E4, pins the reranker to CPU, and prints visible progress throughout long stages.
