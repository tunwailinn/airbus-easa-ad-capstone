# Project Status

Last updated: 4 August 2026

This file records only the active v3.1 project state. Superseded annotation-workflow history remains available in Git history and is not part of the current execution path.

## Current position

- Frozen corpus: **1,809 physical PDF records / 1,808 base AD families**.
- Development corpus: **1,804 PDFs**.
- Held-out unseen set: **5 PDFs from 5 distinct families**.
- Methodology: **section-complete deterministic local extraction + original-PDF page-aware RAG**.
- Content schema: **2.1.0**.
- Local parser: **v2.1.4**.
- Extraction evaluator: **content-eval-v3.1.2**.
- Hosted semantic extraction: **not used**.
- Immutable audit source: `gold_releases/easa_airbus_ad_gold_v2/` with 50 validated records.
- Nominal content split: 30 development / 20 test, seed 42.
- Clean final extraction test: **19 records**, because AD `2024-0038` was used during parser-v2.1.4 diagnosis and is excluded from unbiased test scoring.
- QA benchmark: `evaluation_sets/easa_airbus_ad_qa_50_v2/`, 50 questions.
- Previous generated corpus: `data_processed/canonical_content_v2.1.3/` is stale.
- Corrected v2.1.4 extraction run has been generated locally at `data_processed/runs/local-content-development-1804-v2.1.4/` and awaits v3.1.2 development audit/evaluation before canonical promotion.
- Corrected canonical target: `data_processed/canonical_content_v2.1.4/`.

## Completed

### Corpus and reference data

- Frozen 1,809-record corpus inventory established.
- Stable corpus manifest and extracted-text cache retained at:
  - `step3_pilot/source_metadata/corpus_manifest.parquet`
  - `step3_pilot/source_metadata/corpus_extracted_text.parquet`
- Five non-gold PDFs reserved for unseen-document evaluation.

### Human-validated audit source

- `gold_releases/easa_airbus_ad_gold_v2/` contains the preserved 50-record validated audit release.
- All 30 nominal development records map to approved immutable release records with independent human-review provenance in the release manifest.
- The previous low development F1 was traced partly to an evaluator-design mismatch: semantic gold projections were being exact/string-scored against complete raw PDF sections.
- Direct inspection of the weakest old-score development references found no obvious reason to replace them; the new development-reference audit verifies all 30 systematically without opening clean test labels.

### Local extraction

- Deterministic parser v2.1.3 completed the earlier 1,804-record development run without hosted LLM/API calls.
- Representative PDF spot checks found material v2.1.3 extraction-boundary defects.
- Parser v2.1.4 fixes:
  - printed `Issued:` date precedence;
  - `Foreign AD:` / `Revision:` field separation;
  - repeated EASA page furniture and status-watermark removal;
  - strict section-heading boundaries;
  - cross-page Definitions and Required Actions continuity;
  - Remark contact retention; and
  - appendix exclusion from Remarks.
- The v2.1.4 parser was checked against source PDFs for AD 2024-0038, AD 2024-0097R2, and AD 2025-0058R1.
- The user has regenerated the 1,804-record v2.1.4 run locally.

### Extraction evaluation

- The first 30-record development run had 100% prediction coverage and 100% schema validity, but its old aggregate projection-overlap F1 is not a valid primary v3.1 accuracy metric.
- Evaluator v3.1.2 now separates:
  - stable comparable metadata;
  - secondary family-taxonomy labels;
  - publication/lifecycle identifiers; and
  - raw-section presence, source containment, and contamination.
- The old projection-overlap calculation remains diagnostic only.
- `audit_development_reference.py` checks all 30 development references against frozen hashes, approval provenance, deterministic reprojection, accepted field assertions, evidence spans, and document-text containment without opening locked test labels.

### Test-set leakage disclosure

- AD `2024-0038` is in the nominal 20-record test split.
- Its source PDF was used to diagnose and tune parser v2.1.4.
- It is therefore excluded automatically from clean test scoring.
- The nominal 30/20 frozen split is preserved unchanged for auditability; final extraction accuracy is reported on the remaining clean **n = 19** test cases.

### RAG and application implementation

Implemented in `full_corpus_pipeline/`:

- page/section chunking;
- BM25/FTS5 sparse retrieval;
- local dense embeddings and FAISS support;
- reciprocal-rank fusion;
- local reranking;
- lifecycle filtering;
- corpus QA;
- temporary uploaded-document QA;
- permanent ingestion without retraining;
- duplicate and lifecycle safeguards;
- extraction, retrieval, and QA evaluators; and
- Streamlit prototype.

## Not yet complete

- Run the 30-record development-reference audit locally and inspect its report.
- Rerun the 30-record development evaluation with evaluator v3.1.2.
- Perform fresh representative source-PDF spot checks on regenerated v2.1.4 records.
- Freeze extraction rules after development review.
- Run the clean final extraction evaluation once on the remaining 19 unbiased test records.
- Promote `data_processed/canonical_content_v2.1.4/` after validation.
- Generate/mount page-preserving text for all 1,804 development PDFs.
- Build production E0 and E4 indexes.
- Run locked retrieval and QA metrics.
- Test temporary QA and permanent ingestion on the five unseen PDFs.
- Reach the final 1,809-record corpus after ingestion testing.

## Immediate next actions

1. Run `full_corpus_pipeline.audit_development_reference` on the 30 development references.
2. Run `full_corpus_pipeline.evaluate_extraction --split development` using evaluator v3.1.2.
3. Review per-field mismatches and raw-section containment/contamination; tune only from development evidence if a genuine defect remains.
4. Freeze parser/evaluator behavior.
5. Run the clean test evaluation once; AD `2024-0038` is excluded automatically, leaving n=19.
6. Promote `canonical_content_v2.1.4/` only after the clean evaluation and source spot checks.
7. Produce page-preserving text, then build E0/E4 and run retrieval/QA evaluation.
8. Test and permanently ingest the five unseen PDFs.

## Current blockers

- The v2.1.4 run must pass the revised development audit/evaluation and final clean extraction test before canonical promotion.
- Page-preserving text for the complete 1,804-document retrieval index must be available locally or mounted from the approved data store.
- Supervisor approval of the v3.1 research boundary should be documented before final thesis claims are frozen.

## Reporting boundary

Do not claim:

- that all 1,809 records contain normalized compliance logic;
- that schema validation alone proves semantic correctness;
- that the nominal 20-record test remained fully unseen after the 2024-0038 diagnostic leak;
- that the frozen snapshot is guaranteed to represent the legally current EASA state; or
- that the prototype determines aircraft-specific compliance.

The original PDF passage remains authoritative for complex compliance interpretation and QA citations.
