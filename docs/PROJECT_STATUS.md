# Project Status

This file records the active v3.1 project state.

## Current position

- Frozen physical snapshot: **1,809 PDFs / 1,808 base AD families**.
- Five frozen unseen PDFs remain reserved for ingestion testing.
- Nominal development extraction: **1,804 physical PDFs**.
- Strict Airbus-only development retrieval view: **1,786 PDFs**.
- Frozen parser: **`content-local-v2.1.6`**.
- Extraction evaluator: **`content-eval-v3.1.5`**.
- Corpus scope audit: **`corpus-scope-audit-v1.3`**.
- Verified page-text source: **`page-text-v1.1`**.
- Active retrieval build stage: **`rag-index-build-v1.1`**.
- QA benchmark: **50 locked questions**.

Parser v2.1.6 remains frozen. Locked extraction-test outcomes must not be used to change parser rules.

## Layer A — extraction status

**PASS / FROZEN. Canonical promotion was authorized after the final gates; record it as completed only when the local promotion command/output is explicitly verified.**

Development run:

- requested/successful: **1,804 / 1,804**;
- failures: **0**;
- schema-valid: **100%**;
- primary development count: **28**;
- stable metadata macro F1: **0.9948**;
- applicability-model F1: **0.9929**;
- reference-number F1: **0.8065**;
- superseded-AD-number F1: **1.0000**;
- all five difficult raw-section presence F1 values: **1.0000**;
- source containment: **130/130**;
- detected contamination: **0**.

Clean locked extraction test:

- nominal test: **20**;
- primary clean count: **17** after two holder-scope exclusions plus disclosed `2024-0038` leakage;
- coverage/schema validity: **1.0000 / 1.0000**;
- stable metadata macro F1: **0.9831**;
- applicability-model F1: **0.9222**;
- reference-number F1: **0.9000**;
- superseded-AD-number F1: **0.6667**;
- all five difficult raw-section presence F1 values: **1.0000**;
- source containment: **74/74**;
- detected contamination: **0**.

These are final extraction outcomes, not further tuning targets.

## Final development scope

Scope audit v1.3 over the 1,804 generated development records:

- **1,786 eligible** for the strict Airbus S.A.S. operational view;
- **18 confirmed external/mixed-holder records** retained in the physical/content inventory;
- **0 unknown**.

The scope-only `2012-0088` visual review remains versioned and does not rewrite extracted content or immutable gold.

## Layer B source layer — page-text v1.1

Original-PDF page-preserving extraction was run over the exact 1,786-record strict Airbus development view.

Native extraction result:

- selected documents: **1,786**;
- successful documents: **1,786**;
- failures: **0**;
- total pages: **6,002**;
- native weak-page documents: **1**;
- native weak pages: **1**.

The only weak native page was **AD 2011-0006, page 3**, a graphical Appendix comparing the old hydraulic accumulator design (4 parts / 3 welds) and new design (2 parts / 1 weld). It was reviewed visually and resolved through the versioned, source-hash-bound visual transcription override.

Final verified page source:

- page-text version: **`page-text-v1.1`**;
- visual override count: **1**;
- unresolved weak/OCR documents: **0**;
- unresolved weak/OCR pages: **0**;
- extraction failures: **0**;
- `ready_for_indexing`: **true**.

Canonical local path:

```text
data_processed/page_text_v1_1/operational_airbus/
```

The earlier local folder name `page_text_v1/` is deprecated because it does not identify the verified v1.1 derivative precisely.

## E0 / E4 retrieval stage

The two frozen comparison systems use the exact same 1,786-document `retrieval_manifest.csv` and verified page-text v1.1 source.

### E0 — baseline

- flat page chunks;
- maximum **350 deterministic whitespace-delimited chunk units**;
- local sentence-transformer embeddings;
- FAISS inner-product index;
- **dense-only ranking** during evaluation.

### E4 — proposed system

- section-aware chunks;
- target approximately **250–450 deterministic whitespace-delimited chunk units**, with shorter chunks allowed at section/document boundaries;
- SQLite FTS5/BM25;
- same local sentence-transformer embeddings as E0;
- FAISS dense index;
- reciprocal-rank fusion;
- local cross-encoder reranking;
- metadata/lifecycle controls when applicable.

The chunk-size unit is a reproducible whitespace-split heuristic for chunk construction/reporting, not the sentence-transformer model's subword tokenizer count.

Frozen dense model for the initial E0/E4 comparison:

```text
sentence-transformers/all-MiniLM-L6-v2
```

The research build must not silently fall back to hashing embeddings, numpy-only dense search, or lexical-only reranking.

### Pre-benchmark build check

`rag-index-build-v1.0` successfully used the correct 1,786-document corpus, sentence-transformers backend, and FAISS backend, but its report mixed two different chunk-count heuristics. This produced reported maxima of **383** for E0 and **483** for E4 despite construction limits of 350/450 whitespace units.

No locked retrieval scores were opened. The v1.0 index is retained only as a traceable pre-benchmark implementation artifact and is **not valid for final retrieval evaluation**.

Active corrected build: **`rag-index-build-v1.1`**. It uses one explicit `whitespace_split` count method for construction/reporting, enforces E0 <=350 and E4 <=450 before indexing, and prints a live elapsed-time progress heartbeat during long embedding/index phases.

Build command:

```bash
.venv/bin/python -m full_corpus_pipeline.build_retrieval_experiments \
  --page-text-root data_processed/page_text_v1_1/operational_airbus \
  --output-root data_processed/indexes/rag_v1_1 \
  --experiment all
```

Expected output root:

```text
data_processed/indexes/rag_v1_1/
├── e0_flat_dense/
├── e4_section_hybrid/
└── build_summary.json
```

## Retrieval evaluation next

After the v1.1 indexes build successfully:

1. verify `build_summary.json` reports `rag-index-build-v1.1`, `sentence_transformers`, `faiss_index_flat_ip`, E0 max <=350, and E4 max <=450;
2. freeze those index artifacts before opening locked retrieval scores;
3. evaluate E0 through dense-only retrieval;
4. evaluate E4 through hybrid retrieval with local cross-encoder reranking;
5. report Recall@1/3/5, MRR, nDCG@5, and correct source/page retrieval;
6. compare E0 vs E4 on the same answerable locked QA questions;
7. then run the full 50-question page-cited QA benchmark.

The retrieval evaluator also prints question-by-question progress and refuses to evaluate a build that is not `rag-index-build-v1.1`.

## Remaining boundaries

Do not claim that:

- all 1,809 physical PDFs are Airbus S.A.S.-holder records;
- excluded/mixed-holder records were deleted;
- structured JSON contains fully normalized compliance logic;
- the nominal 20-record extraction test remained fully unseen after the disclosed `2024-0038` leak;
- the single visual page override is native OCR text; or
- the system determines aircraft-specific legal compliance.

Original PDF passages remain authoritative for detailed applicability/compliance interpretation and page-cited QA.
