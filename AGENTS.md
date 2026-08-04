# Agent Guide: Airbus EASA AD Capstone v3.1

Read this before changing code, data rules, experiments, or documentation.

## Project boundary

- Frozen snapshot: **1,809 physical EASA AD PDFs / 1,808 base AD families**.
- Five PDFs remain frozen as unseen ingestion cases.
- Nominal development extraction: **1,804 physical PDFs**.
- Strict operational scope: EU-issued EASA ADs whose Design/Type Approval Holder is Airbus S.A.S., accepting legacy Airbus/Airbus Industrie naming.
- Scope filtering never deletes physical/source records.
- Authoritative methodology: `airbus_easa_ad_project_exact_plan.md`.

## Architecture

```text
Layer A: deterministic section-complete content records
→ metadata lookup, filtering, browsing, raw difficult AD sections

Layer B: original-PDF page text + RAG
→ applicability/compliance retrieval, interpretation, page-cited QA
```

Detailed compliance interpretation must use original PDF passages retrieved by RAG. Do not claim the structured content JSON fully normalizes compliance logic.

## Non-negotiable rules

1. Source PDFs and immutable gold are read-only.
2. Keep one generated content record per nominal physical PDF; operational scope is a separate filter.
3. Never merge passages or requirements from different PDF versions.
4. Keep lifecycle/latest-selection state outside content JSON.
5. Preserve Applicability, Definitions, Reason, Requirements/Compliance, Ref. Publications wording, and Remarks when printed.
6. Do not normalize difficult compliance conditions, intervals, exceptions, or terminating logic across the full corpus.
7. RAG answers must cite AD number, source PDF, page, and section when available.
8. Abstain when retrieved support is incomplete or conflicting.
9. Temporary upload and permanent ingestion do not retrain models.
10. Confirmed external/mixed-holder records remain physically preserved but are excluded from the strict Airbus-only operational view.
11. Missing/malformed/unclassified holders are `unknown`, never automatic exclusions.
12. **Parser v2.1.6 is frozen. Do not modify it from locked extraction-test outcomes.**
13. The disclosed `2024-0038` test leak remains excluded from clean extraction scoring.
14. The five unseen PDFs remain outside development retrieval indexes until unseen-document evaluation.
15. Retrieval experiments must consume verified **page-text v1.1** only; unresolved weak pages or page-text hash failures block indexing.
16. E0 and E4 must use the same 1,786-document retrieval manifest and the same dense embedding model.
17. E0 ranking is dense-only over flat chunks. E4 is section-aware BM25 + dense + FAISS + RRF + local cross-encoder reranking.
18. Do not silently use hashing, numpy-only dense indexing, or lexical reranking fallback for the frozen thesis E0/E4 measurements.
19. Final retrieval evaluation must use **`rag-index-build-v1.1`** from `data_processed/indexes/rag_v1_1/`; the earlier `rag_v1/` build is a rejected pre-benchmark implementation artifact only.
20. Chunk-size reporting uses the same deterministic `whitespace_split` units as the construction limits: E0 <=350 and E4 <=450. These are reproducible chunk units, not transformer subword token counts.

## Frozen/active versions

- Content schema: **2.1.0**.
- Frozen parser: **`content-local-v2.1.6`**.
- Extraction evaluator: **`content-eval-v3.1.5`**.
- Corpus scope audit: **`corpus-scope-audit-v1.3`**.
- Verified page source: **`page-text-v1.1`**.
- Page visual override file: `full_corpus_pipeline/page_text_visual_overrides.json`.
- Active retrieval build stage: **`rag-index-build-v1.1`**.
- QA benchmark: **50 locked questions**.
- Immutable audit source: `gold_releases/easa_airbus_ad_gold_v2/`.

## Frozen extraction results

Development primary count: **28** after holder-scope exclusions.

- 1,804/1,804 generated; zero failures.
- coverage/schema validity: 1.0000/1.0000.
- stable-metadata macro F1: **0.9948**.
- applicability-model F1: **0.9929**.
- reference-number F1: **0.8065**.
- superseded-AD-number F1: **1.0000**.
- all five difficult raw-section presence F1 values: **1.0000**.
- source containment: **130/130**; contamination: **0**.

Clean locked extraction test primary count: **17**.

- coverage/schema validity: 1.0000/1.0000.
- stable-metadata macro F1: **0.9831**.
- applicability-model F1: **0.9222**.
- reference-number F1: **0.9000**.
- superseded-AD-number F1: **0.6667**.
- all five raw-section presence F1 values: **1.0000**.
- source containment: **74/74**; contamination: **0**.

These are final extraction results, not tuning input.

## Final development scope

- Physical development records: **1,804**.
- Strict Airbus-only operational records: **1,786**.
- Retained external/mixed-holder records: **18**.
- Unknown: **0**.

The `2012-0088` source-review override affects scope classification only.

## Verified page-text source layer

The local original-PDF page extraction completed over the exact 1,786-record strict Airbus development view:

- selected documents: **1,786**;
- successful documents: **1,786**;
- failures: **0**;
- total PDF pages: **6,002**;
- native weak pages detected: **1 page in 1 document**;
- reviewed visual override: **AD 2011-0006, page 3**;
- unresolved weak/OCR pages after review: **0**;
- `ready_for_indexing`: **true**;
- verified source version: **`page-text-v1.1`**.

The reviewed page is a graphical Appendix comparing the old hydraulic accumulator design (4 parts / 3 welds) and new design (2 parts / 1 weld). Native text is preserved in provenance fields/backups; only the reviewed page derivative is used for retrieval.

Canonical local path for the verified source layer:

```text
data_processed/page_text_v1_1/operational_airbus/
```

Do not use the former ambiguous `page_text_v1/` path for new experiments.

## Current retrieval experiments

`rag-index-build-v1.0` proved the corpus/model/backend gates but mixed chunk-count heuristics in its report. Because reported maxima appeared as 383 for E0 and 483 for E4, it was rejected before any locked retrieval scores were opened. Preserve it only for traceability.

Build the corrected v1.1 indexes from the same verified page source:

```bash
.venv/bin/python -m full_corpus_pipeline.build_retrieval_experiments \
  --page-text-root data_processed/page_text_v1_1/operational_airbus \
  --output-root data_processed/indexes/rag_v1_1 \
  --experiment all
```

The builder prints live elapsed-time progress during long embedding/index phases and fails if E0 exceeds 350 or E4 exceeds 450 `whitespace_split` chunk units.

Expected outputs:

```text
data_processed/indexes/rag_v1_1/
├── e0_flat_dense/
├── e4_section_hybrid/
└── build_summary.json
```

E0 must be evaluated through `search_dense_only`; E4 through strict hybrid retrieval with local reranking. The evaluator refuses non-v1.1 builds and prints question-by-question progress.

## Immediate priority

1. Pull the current `main` branch and run the full unit-test suite.
2. Build corrected E0 and E4 under `data_processed/indexes/rag_v1_1/`.
3. Verify the v1.1 build summary: 1,786 documents, real sentence-transformers + FAISS backends, E0 max <=350, E4 max <=450.
4. Freeze the v1.1 indexes before opening locked retrieval scores.
5. Run retrieval evaluation once: Recall@1/3/5, MRR, nDCG@5, correct source/page.
6. Run the 50-question page-cited QA benchmark.
7. Evaluate temporary uploaded-PDF QA.
8. Permanently ingest the five frozen unseen PDFs without retraining.

## Working protocol

Authority order:

1. current user request;
2. this file;
3. `airbus_easa_ad_project_exact_plan.md`;
4. `docs/PROJECT_STATUS.md`;
5. `docs/DECISIONS.md`;
6. `docs/BENCHMARK_DESIGN.md`;
7. `docs/PAGE_TEXT_PIPELINE.md`.

After material work, preserve unrelated artifacts, run relevant tests, update project status, and record stable methodology changes. Never reopen frozen extraction tuning from locked-test failures.
