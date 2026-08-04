# Agent Guide: Airbus EASA AD Capstone v3.1

Read this before changing code, data rules, experiments, or documentation.

## Project boundary

- Frozen snapshot: **1,809 physical Airbus-related EASA AD PDFs / 1,808 base AD families**.
- Five PDFs are frozen as unseen ingestion cases.
- Nominal development extraction: **1,804 physical PDFs**.
- Strict operational scope: EU-issued EASA ADs whose Design/Type Approval Holder is Airbus S.A.S., accepting legacy Airbus/Airbus Industrie naming.
- Scope filtering does not delete physical/source records.
- Authoritative methodology: `airbus_easa_ad_project_exact_plan.md`.

## Architecture

```text
Section-complete deterministic content records
→ reliable metadata + raw difficult AD sections

Original PDF page chunks + RAG
→ compliance timing, conditions, exceptions, branches, cross-references, QA
```

Detailed compliance interpretation must use original PDF passages retrieved by RAG. Do not claim extracted JSON contains fully normalized compliance logic.

## Non-negotiable rules

1. Source PDFs and immutable gold are read-only.
2. Keep one generated content record per nominal physical PDF; operational scope is a separate filter.
3. Never merge passages or requirements from different PDF versions.
4. Keep lifecycle/latest-selection state outside content JSON.
5. Do not add evidence/confidence/review/model metadata to content records.
6. Preserve Applicability, Definitions, Reason, Requirements/Compliance, reference wording, and Remarks when printed.
7. Do not normalize difficult compliance conditions, intervals, exceptions, or terminating logic across the full corpus.
8. RAG answers must cite AD number, source PDF, page, and section when available.
9. Abstain when retrieved support is incomplete or conflicting.
10. Temporary upload and permanent ingestion do not retrain models.
11. Printed PDF metadata is authoritative over stale manifest metadata when directly readable.
12. Confirmed external/mixed-holder records remain physically preserved but are excluded from the strict Airbus-only operational view.
13. Missing/malformed/unclassified holders are `unknown`, never automatic exclusions.
14. **Parser v2.1.6 is frozen. Do not modify it based on locked extraction-test results.**
15. The disclosed `2024-0038` test leak remains excluded from clean extraction scoring; never replace it with another record.

## Frozen versions

- Content schema: **2.1.0**.
- Frozen parser: **`content-local-v2.1.6`** via `local_extractor_v216.py`.
- Underlying preserved parser: `content-local-v2.1.5` in `local_extractor.py`.
- Extraction evaluator: **`content-eval-v3.1.5`**.
- Corpus scope audit: **`corpus-scope-audit-v1.3`**.
- Scope policy: `full_corpus_pipeline/scope_policy.py`.
- Versioned manual scope reviews: `full_corpus_pipeline/scope_review_overrides.json`.
- Immutable audit source: `gold_releases/easa_airbus_ad_gold_v2/`.
- Nominal extraction benchmark: 30 development / 20 test, seed 42.
- QA benchmark: 50 locked questions.

## Frozen extraction results

Development primary count: **28** after excluding `2024-0095` and `2026-0079` for holder scope.

Development result:

- 1,804/1,804 generated; zero failures;
- prediction coverage/schema validity: 1.0000/1.0000;
- stable-metadata macro F1: **0.9948**;
- applicability-model F1: **0.9929**;
- reference-number F1: **0.8065**;
- superseded-AD-number F1: **1.0000**;
- all five raw-section presence F1 values: **1.0000**;
- raw-section source containment: **130/130**;
- contamination: **0**.

Strict development scope view:

- physical generated records: **1,804**;
- eligible Airbus-only operational records: **1,786**;
- retained external/mixed-holder records: **18**;
- unknown: **0**.

One reviewed override resolves `2012-0088` as Airbus based on visual original-PDF page 1 because its native text cache is column-garbled. The override affects scope only.

Clean locked test:

- nominal 20;
- exclude mixed-holder `2011-0098`, Airbus Defence `2021-0286`, and leaked `2024-0038`;
- primary count: **17**;
- prediction coverage/schema validity: 1.0000/1.0000;
- stable-metadata macro F1: **0.9831**;
- applicability-model F1: **0.9222**;
- reference-number F1: **0.9000**;
- superseded-AD-number F1: **0.6667**;
- all five raw-section presence F1 values: **1.0000**;
- raw-section source containment: **74/74**;
- contamination: **0**.

These test outcomes are final extraction results, not tuning input.

## Extraction status

**PASS / FROZEN.** The extraction stage is ready for reproducible local canonical promotion.

The connected sandbox reproduced the extraction/evaluation gates, but the official local workspace should regenerate the run using the versioned CLI to create the canonical provenance sidecars before promotion.

## Common local reproduction commands

```bash
.venv/bin/python -m unittest discover -s full_corpus_pipeline/tests -v

.venv/bin/python -m full_corpus_pipeline.extract_corpus \
  --run-id local-content-development-1804-v2.1.6

.venv/bin/python -m full_corpus_pipeline.audit_development_reference \
  --output data_processed/runs/local-content-development-1804-v2.1.6/development_reference_audit.json

.venv/bin/python -m full_corpus_pipeline.audit_corpus_scope \
  data_processed/runs/local-content-development-1804-v2.1.6/records \
  --output data_processed/runs/local-content-development-1804-v2.1.6/corpus_scope_audit.json

.venv/bin/python -m full_corpus_pipeline.evaluate_extraction \
  data_processed/runs/local-content-development-1804-v2.1.6/records \
  --output data_processed/runs/local-content-development-1804-v2.1.6/evaluation_development_v3.1.5.json \
  --split development

.venv/bin/python -m full_corpus_pipeline.evaluate_extraction \
  data_processed/runs/local-content-development-1804-v2.1.6/records \
  --output data_processed/runs/local-content-development-1804-v2.1.6/evaluation_test_clean_v3.1.5.json \
  --split test

.venv/bin/python -m full_corpus_pipeline.promote_extraction_run \
  data_processed/runs/local-content-development-1804-v2.1.6 \
  data_processed/canonical_content_v2.1.6 \
  --expected-count 1804
```

## Immediate priority

1. Reproduce/promote `canonical_content_v2.1.6/` locally.
2. Generate page-preserving original-PDF text.
3. Build E0 flat dense-only and E4 section-aware hybrid indexes.
4. Run retrieval evaluation.
5. Run the 50-question page-cited QA benchmark.
6. Test temporary uploaded-PDF QA.
7. Permanently ingest the five unseen PDFs without retraining.

## Working protocol

Authority order:

1. current user request;
2. this file;
3. `airbus_easa_ad_project_exact_plan.md`;
4. `docs/PROJECT_STATUS.md`;
5. `docs/DECISIONS.md`;
6. `docs/BENCHMARK_DESIGN.md`.

After material work, preserve unrelated artifacts, run relevant tests, update project status, and record stable methodology changes. Never reopen frozen extraction tuning from locked-test failures.
