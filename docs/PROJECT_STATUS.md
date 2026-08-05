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
- Frozen retrieval build: **`rag-index-build-v1.2`**.
- Retrieval evaluator: **`retrieval-eval-v1.3`**, locked to v1.2 with PyTorch/FAISS/cross-encoder process isolation on macOS ARM.
- QA benchmark: **50 locked questions**, of which **44** are answerable-from-AD retrieval questions and 6 are reserved for abstention/full-QA evaluation.

Parser v2.1.6 remains frozen. Locked extraction-test outcomes must not be used to change parser rules.

## Layer A — extraction status

**PASS / FROZEN.**

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

## Layer B source layer — page-text v1.1

Original-PDF page-preserving extraction was run over the exact 1,786-record strict Airbus development view.

Final verified page source:

- selected/successful documents: **1,786 / 1,786**;
- failures: **0**;
- total pages: **6,002**;
- one native weak page: **AD 2011-0006, page 3**;
- reviewed visual override count: **1**;
- unresolved weak/OCR documents/pages: **0 / 0**;
- `ready_for_indexing`: **true**;
- page-text version: **`page-text-v1.1`**.

Canonical local path:

```text
data_processed/page_text_v1_1/operational_airbus/
```

## E0 / E4 retrieval stage — BUILD ACCEPTED / FROZEN

The accepted benchmark-eligible build is **`rag-index-build-v1.2`** under:

```text
data_processed/indexes/rag_v1_2/
```

No locked retrieval scores were opened before this build was accepted.

### Common frozen configuration

- corpus: same **1,786** strict-scope documents for E0 and E4;
- embedding model: `sentence-transformers/all-MiniLM-L6-v2`;
- dense backend: `sentence_transformers`;
- dense index: `faiss_index_flat_ip`;
- chunk-size count method: `whitespace_split`.

### E0 — baseline

- flat page chunks;
- chunk count: **9,394**;
- max chunk size: **350**;
- multi-page chunks: **0**;
- evaluation ranking: **dense-only**.

### E4 — proposed system

- section-aware chunks;
- target approximately **250–450** chunk units, shorter chunks allowed at boundaries;
- chunk count: **12,634**;
- max chunk size: **450**;
- multi-page chunks: **2,924**;
- max page span: **5**;
- SQLite FTS5/BM25;
- same dense model + FAISS;
- reciprocal-rank fusion;
- reranker: `cross-encoder/ms-marco-MiniLM-L-6-v2`;
- frozen candidate depth: **20** per sparse/dense path.

### Build history

- `rag-index-build-v1.0`: rejected before benchmark because chunk-size reporting mixed incompatible counters.
- `rag-index-build-v1.1`: valid E0, but E4 stopped before embedding when a 476-unit section chunk violated the 450 maximum.
- `rag-index-build-v1.2`: E4 construction accounting corrected; full build passed and is frozen for evaluation.

Older `rag_v1/` and `rag_v1_1/` workspaces are retained for audit history only and must not be used for final retrieval evaluation.

## Retrieval evaluation — COMPLETED, PLUMBING REVIEW IN PROGRESS

A complete `retrieval-eval-v1.3` comparison artifact has now been produced using the frozen v1.2 indexes and the macOS ARM process-isolated runtime.

Observed aggregate results over the 44 answerable retrieval questions:

### E0 observed

- Recall@1/3/5: **0.0000 / 0.0000 / 0.0000**;
- MRR: **0.0000**;
- nDCG@5: **0.0000**;
- correct-source@1/@5: **0.0000 / 0.0000**;
- correct-source+page@1/@5: **0.0000 / 0.0000**.

### E4 observed

- Recall@1: **0.2500**;
- Recall@3: **0.3636**;
- Recall@5: **0.4091**;
- MRR: **0.3106**;
- nDCG@5: **0.3353**;
- correct-source@1: **0.2727**;
- correct-source@5: **0.5000**;
- correct-source+page@1: **0.2500**;
- correct-source+page@5: **0.4091**;
- paired comparison: **E4 better 18 / E0 better 0 / ties 26**.

These values are **observed but not yet promoted to final thesis results** because E0's all-zero outcome warrants a post-evaluation plumbing audit. This audit is allowed because it checks implementation correctness after the frozen comparison; it must not tune chunking, models, candidate depth, fusion, reranker, corpus membership, lifecycle rules, questions, or metric definitions.

Current diagnostic tool:

```text
full_corpus_pipeline/diagnose_retrieval_evaluation.py
```

It verifies:

1. FAISS row positions align with `chunks.jsonl` and `dense_embeddings.npy`;
2. stored embeddings agree with fresh encodings from the frozen MiniLM model;
3. every benchmark target AD is actually present in E0/E4 indexes;
4. whether target AD identifiers occur literally in the locked questions; and
5. target source/page candidate recall at depth 20 for E0 dense, E4 dense, and E4 BM25 branches.

The current benchmark composition is also noted for interpretation: the 44 answerable questions reference **8 distinct target ADs**, with **25/44 targeting AD 2006-0047**. This is a reporting limitation/characteristic, not a reason to alter the locked benchmark after results are observed.

Do not start hosted-LLM QA scoring until the plumbing diagnostic is reviewed. If plumbing passes, report the frozen E0/E4 retrieval results as observed, including the zero E0 baseline and the benchmark-composition limitation. If plumbing fails, correct only the implementation defect, document it, and rerun the same frozen benchmark without changing retrieval configuration.

## Remaining boundaries

Do not claim that:

- all 1,809 physical PDFs are Airbus S.A.S.-holder records;
- excluded/mixed-holder records were deleted;
- structured JSON contains fully normalized compliance logic;
- the nominal 20-record extraction test remained fully unseen after the disclosed `2024-0038` leak;
- the single visual page override is native OCR text; or
- the system determines aircraft-specific legal compliance.

Original PDF passages remain authoritative for detailed applicability/compliance interpretation and page-cited QA.
