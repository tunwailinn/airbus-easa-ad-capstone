# Retrieval Build Status

Last updated: 5 August 2026

This file records the active pre-benchmark E0/E4 index-build state. Locked retrieval scores have **not** been opened.

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

The first infrastructure build completed, but its report used a lexical token counter that differed from the whitespace-based construction heuristic. Reported maxima were therefore inconsistent with the declared chunk policy. No locked retrieval scores were opened.

### `rag-index-build-v1.1` — partial, not benchmark-eligible

E0 built successfully over all 1,786 documents:

- chunks: **9,394**;
- dense backend: sentence-transformers;
- dense index: FAISS IndexFlatIP;
- declared/verified flat limit: **350 whitespace-delimited units**.

E4 stopped **before embedding/index construction** because the new strict build gate found a real section-chunker mismatch:

```text
E4-section-hybrid: max chunk size 476 exceeds frozen limit 450
```

Root cause: the legacy section chunker accounted blocks with `TOKEN_RE.findall(...)` while the frozen v1.1 report/limit used whitespace-delimited units. Punctuation-only or formatting units could therefore be omitted during construction accounting and produce a chunk larger than 450.

No E4 v1.1 index was accepted and no locked benchmark scores were opened.

### `rag-index-build-v1.2` — active required build

v1.2 fixes E4 at the construction boundary. Section chunk accounting, oversized-block splitting, and build reporting now all use the same whitespace-delimited size policy.

Frozen limits:

- E0 flat maximum: **350**;
- E4 section-aware target: **250–450**;
- maximum E4 chunk size: **450**.

v1.2 also supports copying/reusing the already validated v1.1 E0 artifact into a new v1.2 workspace. E0 logic is unchanged; the copied artifact is validated again for document count, model, FAISS backend, chunk policy, maximum size, and required files before reuse.

## Required local build

Keep the earlier workspaces for audit history:

```text
data_processed/indexes/rag_v1/
data_processed/indexes/rag_v1_1/
```

Build the new workspace with:

```bash
.venv/bin/python -m full_corpus_pipeline.build_retrieval_experiments \
  --page-text-root data_processed/page_text_v1_1/operational_airbus \
  --output-root data_processed/indexes/rag_v1_2 \
  --reuse-e0-from data_processed/indexes/rag_v1_1/e0_flat_dense \
  --experiment all
```

Expected behavior:

1. validate page-text v1.1;
2. validate the existing E0 v1.1 artifact;
3. copy/revalidate E0 into `rag_v1_2/e0_flat_dense` without recomputing embeddings;
4. rebuild E4 with strict whitespace-based section accounting;
5. reject the build if E4 exceeds 450;
6. embed/index E4 with visible elapsed-time progress;
7. write `data_processed/indexes/rag_v1_2/build_summary.json` only after both experiments pass.

## Benchmark lock

Do **not** run `evaluate_retrieval_experiments.py` until the v1.2 `build_summary.json` is reviewed and accepted. The E0/E4 retrieval configuration remains frozen before observing locked retrieval performance.
