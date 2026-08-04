# Agent Guide: Airbus EASA AD Capstone v3.1

Read this before changing code, data rules, experiments, or documentation.

## Project boundary

- Frozen snapshot: 1,809 physical Airbus-related EASA AD PDFs / 1,808 base AD families.
- Stated research scope: EU-issued EASA ADs whose Design/Type Approval Holder is Airbus S.A.S., accepting legacy Airbus/Airbus Industrie naming.
- Nominal development extraction: 1,804 PDFs after reserving five unseen PDFs.
- The frozen snapshot is not assumed to be perfectly scope-clean; holder-scope audits must be run before canonical claims/counts are frozen.
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
2. Keep one content record per physical PDF during extraction; scope eligibility is an evaluation/corpus-governance decision, not a reason to rewrite source artifacts silently.
3. Never merge passages or requirements from different PDF versions.
4. Keep lifecycle/latest-selection state outside content JSON.
5. Keep generated predictions separate from the immutable 50-record audit source.
6. Do not add evidence spans, confidence, review status, model metadata, or machine-status labels to content records.
7. Preserve Applicability, Definitions, Reason, Requirements/Compliance, reference wording, and Remarks when printed.
8. Do not machine-normalize difficult compliance conditions, intervals, exceptions, or terminating logic across the full corpus.
9. RAG answers must cite AD number, source PDF, page, and section when available.
10. Abstain when retrieved support is incomplete or conflicting.
11. Temporary upload and permanent ingestion do not retrain models.
12. Printed PDF metadata is authoritative over stale manifest metadata when the parser can read it directly.
13. Do not promote a generated corpus after a parser-version change until the corpus has been regenerated and re-evaluated.
14. Primary extraction metrics must enforce the stated Airbus S.A.S. holder scope from reviewed gold metadata and report exclusions explicitly.
15. Do not use known leaked test cases for clean final scoring; preserve the nominal frozen split and disclose exclusions instead of replacing members.

## Active versions and artifacts

- Content schema: `2.1.0`.
- Local deterministic parser: `v2.1.4`.
- Extraction evaluator: `content-eval-v3.1.4`.
- Previous generated corpus: `data_processed/canonical_content_v2.1.3/` — stale.
- Regenerated run: `data_processed/runs/local-content-development-1804-v2.1.4/`.
- Corrected canonical target after validation: `data_processed/canonical_content_v2.1.4/`.
- Immutable audit source: `gold_releases/easa_airbus_ad_gold_v2/`.
- Nominal content evaluation set: `evaluation_sets/easa_airbus_ad_content_gold_50_v2/`, 30 development / 20 test.
- Known benchmark exclusions:
  - development `2026-0079`: Lufthansa Technik AG holder, outside Airbus S.A.S. scope;
  - test `2021-0286`: Airbus Defence and Space S.A., outside Airbus S.A.S. scope;
  - test `2024-0038`: source PDF used during parser v2.1.4 diagnosis, so excluded from clean test scoring.
- QA benchmark: `evaluation_sets/easa_airbus_ad_qa_50_v2/`.
- Unseen set: `evaluation_sets/unseen_incoming_5_v1/`.
- Corpus reference files used by active code:
  - `step3_pilot/source_metadata/corpus_manifest.parquet`
  - `step3_pilot/source_metadata/corpus_extracted_text.parquet`

## Parser v2.1.4 boundary rules

- Strip repeated EASA page furniture/status watermarks before section segmentation.
- Do not treat ordinary prose beginning with `compliance`, `contact`, or similar words as a new section unless it is an actual labelled heading.
- Preserve sections across page boundaries.
- Keep `Foreign AD`, revision, supersedure, and other header fields separate.
- Use printed `Issued:` date before manifest fallback.
- Keep Remark contact lines and stop Remarks before later appendices/annexes.

## Extraction evaluation rules

- Run `audit_development_reference.py` before tuning from the nominal 30 development references.
- Run `audit_corpus_scope.py` on the regenerated 1,804 records before canonical promotion.
- Primary metadata metrics compare only representation-compatible facts with safe normalization.
- Aircraft-family taxonomy is secondary.
- Reference numbers and superseded AD numbers are scored separately.
- Raw difficult sections are evaluated for presence, source-text containment, and page-furniture contamination rather than exact semantic-projection overlap.
- The old flatten/set overlap remains diagnostic only.
- Never tune from clean test labels.

## Primary retrieval experiment

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

Before work, inspect current inputs/outputs and preserve unrelated changes. After material work, run relevant tests, update project status, and record stable methodology changes in `docs/DECISIONS.md`.

## Common commands

```bash
.venv/bin/python -m unittest discover -s full_corpus_pipeline/tests -v

.venv/bin/python -m full_corpus_pipeline.audit_development_reference \
  --output data_processed/runs/local-content-development-1804-v2.1.4/development_reference_audit.json

.venv/bin/python -m full_corpus_pipeline.audit_corpus_scope \
  data_processed/runs/local-content-development-1804-v2.1.4/records \
  --output data_processed/runs/local-content-development-1804-v2.1.4/corpus_scope_audit.json

.venv/bin/python -m full_corpus_pipeline.evaluate_extraction \
  data_processed/runs/local-content-development-1804-v2.1.4/records \
  --output data_processed/runs/local-content-development-1804-v2.1.4/evaluation_development_v3.1.4.json \
  --split development
```

## Immediate priority

1. Run the 30-reference development audit.
2. Run the full 1,804-record holder-scope audit and resolve any corpus-scope discrepancy before canonical promotion.
3. Rerun development extraction evaluation with evaluator v3.1.4 and inspect genuine mismatches/raw-section integrity.
4. Freeze parser/evaluator behavior, then run the clean test once with automatic scope/leakage exclusions.
5. Promote `canonical_content_v2.1.4/` only after validation and corpus-scope policy is resolved.
6. Build page-aware E0/E4 indexes, run retrieval/QA evaluation, then test permanent ingestion of the five unseen PDFs.
