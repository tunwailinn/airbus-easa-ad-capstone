# Agent Guide: Airbus EASA AD Capstone v3.1

Read this before changing code, data rules, experiments, or documentation.

## Project boundary

- Frozen corpus: 1,809 physical Airbus S.A.S. EASA AD PDFs / 1,808 base AD families.
- Development corpus: 1,804 PDFs.
- Held-out unseen set: 5 PDFs.
- Final corpus after ingestion evaluation: 1,809 PDFs.
- Authoritative methodology: `airbus_easa_ad_project_exact_plan.md`.

## Architecture

```text
Section-complete content records
→ reliable metadata + raw difficult AD sections

Original PDF page chunks + RAG
→ compliance timing, conditions, exceptions, branches, cross-references, QA
```

Do not claim that the extracted corpus contains fully normalized compliance logic. Detailed compliance interpretation must use original PDF passages retrieved by RAG.

## Non-negotiable rules

1. Treat source PDFs as immutable.
2. Keep one content record per physical PDF.
3. Never merge passages or requirements from different PDF versions.
4. Keep lifecycle/latest-selection state outside content JSON.
5. Keep generated predictions separate from the immutable 50-record audit source.
6. Do not add evidence spans, confidence, review status, model metadata, or machine-status labels to content records.
7. Preserve Applicability, Definitions, Reason, Requirements/Compliance, reference wording, and Remarks when printed.
8. Do not machine-normalize difficult compliance conditions, intervals, exceptions, or terminating logic across the full corpus.
9. RAG answers must cite AD number, source PDF, page, and section when available.
10. Abstain when retrieved support is incomplete or conflicting.
11. Temporary upload and permanent ingestion do not retrain models.

## Active versions and artifacts

- Content schema: `2.1.0`.
- Local deterministic parser: `v2.1.3`.
- Active generated corpus: `data_processed/canonical_content_v2.1.3/`.
- Immutable audit source: `gold_releases/easa_airbus_ad_gold_v2/`.
- Active content evaluation set: `evaluation_sets/easa_airbus_ad_content_gold_50_v2/`.
- QA benchmark: `evaluation_sets/easa_airbus_ad_qa_50_v2/`.
- Unseen set: `evaluation_sets/unseen_incoming_5_v1/`.
- Corpus reference files used by active code:
  - `step3_pilot/source_metadata/corpus_manifest.parquet`
  - `step3_pilot/source_metadata/corpus_extracted_text.parquet`

## Primary experiment

- E0: flat chunks + dense-only retrieval.
- E4: section-aware BM25 + dense retrieval + FAISS + RRF + reranking + metadata/lifecycle filtering.

## Working protocol

Authority order:

1. current user request;
2. this file;
3. `airbus_easa_ad_project_exact_plan.md`;
4. `docs/PROJECT_STATUS.md`;
5. `docs/DECISIONS.md`;
6. `docs/BENCHMARK_DESIGN.md`.

Before work, inspect the current inputs/outputs and preserve unrelated changes. After material work, run relevant tests, update project status, and record stable methodology changes in `docs/DECISIONS.md`.

## Common commands

```bash
.venv/bin/python -m unittest discover -s full_corpus_pipeline/tests -v

.venv/bin/python -m full_corpus_pipeline.extract_corpus \
  --run-id local-content-development-1804-v2.1.3

.venv/bin/python -m full_corpus_pipeline.retrieval \
  --page-text-dir /approved/page_text \
  --manifest step3_pilot/source_metadata/corpus_manifest.parquet \
  --exclude-selection evaluation_sets/unseen_incoming_5_v1/selection.csv \
  --output-dir indexes/corpus_v1
```

## Immediate priority

1. Human spot-check content/raw-section boundaries and QA references.
2. Build page-aware E0 and E4 indexes for the 1,804 development PDFs.
3. Run locked retrieval/QA evaluation.
4. Test temporary QA and permanent ingestion on the five held-out PDFs.
5. Confirm final 1,809-record corpus.
