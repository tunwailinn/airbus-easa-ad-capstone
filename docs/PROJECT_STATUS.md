# Project Status

Last updated: 4 August 2026

This file records the active v3.1 project state.

## Current position

- Frozen physical snapshot: **1,809 PDFs / 1,808 base AD families**.
- Five frozen unseen PDFs remain reserved for ingestion testing.
- Nominal development extraction: **1,804 physical PDFs**.
- Strict operational research scope: EU-issued EASA ADs whose Design/Type Approval Holder is Airbus S.A.S., accepting legacy Airbus/Airbus Industrie naming.
- Content schema: **2.1.0**.
- Frozen local parser: **`content-local-v2.1.6`**.
- Extraction evaluator: **`content-eval-v3.1.5`**.
- Corpus scope audit: **`corpus-scope-audit-v1.3`**.
- Hosted extraction/model calls: **none**.
- Immutable audit source: `gold_releases/easa_airbus_ad_gold_v2/`.
- Nominal extraction benchmark: 30 development / 20 test, seed 42.
- QA benchmark remains 50 locked questions.

Parser v2.1.6 is now **frozen**. Locked-test results must not be used to change parser rules.

## Development reference

The nominal 30 development references retain:

- 28 primary scope-eligible records;
- `2024-0095` excluded from primary scoring because the holder is Airbus Defence and Space S.A.;
- `2026-0079` excluded because the holder is Lufthansa Technik AG;
- zero critical reference-audit issues.

The immutable gold release and nominal split are unchanged.

## Final v2.1.6 development gate

A sandbox reproduction used the frozen 1,809-row document-text cache and the exact five-document holdout boundary, producing the nominal 1,804 development records with parser v2.1.6.

Run-level result:

- requested: **1,804**;
- successful: **1,804**;
- failures: **0**;
- schema-valid: **100%**;
- hosted execution: **false**.

Primary 28-record development result:

- prediction coverage: **1.0000**;
- schema validity: **1.0000**;
- stable-metadata macro F1: **0.9948**;
- applicability-model F1: **0.9929**;
- reference-number F1: **0.8065**;
- superseded-AD-number F1: **1.0000**;
- reference/lifecycle macro F1: **0.9032**.

Raw difficult-section result:

- Definitions presence F1: **1.0000**;
- Reason presence F1: **1.0000**;
- Required Actions/Compliance presence F1: **1.0000**;
- Ref. Publications text presence F1: **1.0000**;
- Remarks presence F1: **1.0000**;
- source containment: **130/130 = 1.0000**;
- detected page-furniture/status contamination: **0**.

The residual development differences are documented limitations rather than reasons for further tuning: broad-vs-expanded model representation in one legacy case, minor Airbus/Airbus-S.A.S. and dash typography normalization, secondary family taxonomy, and incomplete-but-high-precision publication-reference recall.

## Final corpus scope view

Scope audit v1.3 over the 1,804 generated development records resolves to:

- **1,786 eligible** for the strict Airbus-only operational view;
- **18 confirmed external/mixed-holder records** retained in the physical/content inventory but excluded from that operational view;
- **0 unknown**.

The 18 retained exclusions include Air France, Jet Aviation Basel, Short Brothers, Fokker Services, Elbe Flugzeugwerke, Airbus Defence and Space, and Lufthansa Technik approval-holder cases.

One source-review override is versioned for `2012-0088`: its document-level native text is column-garbled, while visual review of original PDF page 1 clearly identifies Airbus as Design Approval Holder. The override affects scope classification only; it does not rewrite extracted content, source PDFs, or immutable gold.

The physical development corpus therefore remains **1,804 records**. The strict Airbus-only operational subset is **1,786 records**.

## Clean locked extraction test

Parser v2.1.6 was frozen before opening/scoring the remaining locked test labels.

Nominal test membership: **20**.

Primary clean-test exclusions:

- `2011-0098`: mixed approval holders (`Airbus; The Boeing Company; Fokker Services`) — outside strict Airbus-only scope;
- `2021-0286`: Airbus Defence and Space S.A. — outside strict Airbus-only scope;
- `2024-0038`: previously used during parser diagnosis — disclosed test leakage.

Clean primary test count: **17**.

Frozen-parser clean-test result:

- prediction coverage: **1.0000**;
- schema validity: **1.0000**;
- stable-metadata macro F1: **0.9831**;
- applicability-model F1: **0.9222**;
- reference-number F1: **0.9000**;
- superseded-AD-number F1: **0.6667**;
- reference/lifecycle macro F1: **0.7833**.

Raw difficult-section result on the 17 clean test records:

- every expected Definitions, Reason, Required Actions/Compliance, Ref. Publications text, and Remarks section was present;
- each raw-section presence F1: **1.0000**;
- source containment: **74/74 = 1.0000**;
- detected page-furniture/status contamination: **0**.

No parser changes are permitted in response to these test results. Remaining structured mismatches are final extraction-test outcomes and should be reported as limitations.

## Extraction-stage decision

**PASS. Parser v2.1.6 is frozen and the extraction stage is ready for canonical reproduction/promotion.**

The connected sandbox reproduced the 1,804-run and evaluation gates, but the user's official local `data_processed/` run should still be regenerated from the updated `main` branch before local canonical promotion so the local provenance sidecars/manifests are produced by the versioned CLI.

Required local reproduction:

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

Do not alter parser behavior if the reproduced locked-test report differs slightly because of environment/version artifacts; investigate reproducibility separately and preserve the frozen test result.

## Next project stage

After canonical local promotion:

1. generate page-preserving original-PDF text for the scope-approved corpus;
2. build E0 flat dense-only and E4 section-aware hybrid indexes;
3. run retrieval Recall@1/3/5, MRR, nDCG@5 and correct source/page evaluation;
4. run the 50-question page-cited QA benchmark;
5. evaluate temporary uploaded-PDF QA;
6. permanently ingest the five frozen unseen PDFs without retraining.

## Reporting boundaries

Do not claim that:

- all 1,809 physical PDFs are Airbus S.A.S.-holder records;
- excluded/mixed-holder physical records were deleted;
- structured JSON contains fully normalized compliance logic;
- the nominal 20-record test remained fully unseen after the disclosed `2024-0038` leak; or
- the system determines aircraft-specific legal compliance.

Original PDF passages remain authoritative for complex compliance interpretation and page-cited QA.
