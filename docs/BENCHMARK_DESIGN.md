# Benchmark Design v3.1

## Evaluation principle

Evaluate the two application layers separately:

- deterministic extraction measures reliable structured metadata plus faithful preservation of raw AD sections;
- retrieval/QA measures evidence selection and interpretation from original PDF passages.

Complex compliance questions are not expected to be answerable from structured fields alone.

## Content extraction reference

Immutable audit source:

```text
gold_releases/easa_airbus_ad_gold_v2/
```

Active derived dataset:

```text
evaluation_sets/easa_airbus_ad_content_gold_50_v2/
```

The immutable annotations contain independently reviewed structured values and source evidence. The derived content projection may represent difficult source material as reviewed semantic units, while the live parser preserves complete printed raw sections. These representations are not exact-string scored against one another.

## Frozen nominal split

- development: 30 records;
- locked test: 20 records;
- grouping key: `base_ad_number`;
- seed: 42.

Nominal membership remains immutable for traceability. Primary scores use project-scope-eligible records and disclose exclusions.

## Scope eligibility

Research scope: EU-issued EASA ADs whose Design/Type Approval Holder is Airbus S.A.S., accepting legacy Airbus/Airbus Industrie naming.

Development primary exclusions:

- `2024-0095` — Airbus Defence and Space S.A.;
- `2026-0079` — Lufthansa Technik AG.

Primary development count: **28**.

Clean-test primary exclusions:

- `2011-0098` — mixed holders (`Airbus; The Boeing Company; Fokker Services`);
- `2021-0286` — Airbus Defence and Space S.A.;
- `2024-0038` — known parser-tuning leakage from earlier diagnosis.

Primary clean-test count: **17**.

The physical generated corpus remains one record per nominal PDF. Confirmed external/mixed-holder records are filtered only from the strict Airbus-only operational view; they are never deleted to manufacture a cleaner source count.

## Extraction evaluator

Active evaluator: `content-eval-v3.1.5` in `full_corpus_pipeline/evaluate_extraction.py`.

### Primary stable metadata

Report precision, recall, F1 and record-exact accuracy for:

- AD number, authority, document type, revision/emergency/correction state;
- Design/Type Approval Holder;
- subject, issue/effective dates and ATA codes;
- manufacturer;
- TCDS identifiers;
- Foreign AD status; and
- detailed applicability-model identifiers.

`stable_metadata_macro_f1` is the primary structured extraction summary.

### Secondary catalogue normalization

Publication-header model identifiers and aircraft-family labels are secondary diagnostics because reviewed gold may expand broad printed family wording into individual variants.

### Reference/lifecycle identifiers

Report:

- `reference_number_f1`;
- `superseded_ad_number_f1`;
- `reference_lifecycle_macro_f1`.

Reference precision is preferred over speculative identifier mining.

### Raw difficult sections

For Definitions, Reason, Required Actions/Compliance, Ref. Publications wording, and Remarks, report:

- source-heading expected presence;
- prediction presence;
- source-text containment after layout-furniture cleanup; and
- page-furniture/status contamination.

`legacy_projection_overlap` is diagnostic only.

## Frozen parser

Active/frozen parser: **`content-local-v2.1.6`**.

v2.1.6 was tuned only from development/source-format evidence. It was frozen before locked-test scoring. No parser changes are permitted in response to the test result.

## Final development result

The exact nominal 1,804 development boundary was reproduced from the frozen 1,809-row text cache and five-document holdout selection.

Run-level gate:

- requested: **1,804**;
- success: **1,804**;
- failures: **0**;
- schema-valid: **100%**.

Primary 28-record metrics:

| Metric | Result |
|---|---:|
| Prediction coverage | 1.0000 |
| Schema validity | 1.0000 |
| Stable metadata macro F1 | **0.9948** |
| Applicability-model F1 | **0.9929** |
| Reference-number F1 | **0.8065** |
| Superseded-AD-number F1 | **1.0000** |
| Reference/lifecycle macro F1 | **0.9032** |

Raw-section result:

- all five raw-section presence F1 values: **1.0000**;
- source containment: **130/130 = 1.0000**;
- contamination detections: **0**.

Residual development differences are retained as documented limitations rather than further tuning targets: broad-vs-expanded model representation, minor Airbus/Airbus-S.A.S./typographic normalization differences, secondary family taxonomy, and incomplete but high-precision publication-reference recall.

## Final operational scope audit

Active scope audit: **`corpus-scope-audit-v1.3`**.

Final development view:

- physical/generated records: **1,804**;
- strict Airbus-only eligible: **1,786**;
- retained external/mixed-holder records: **18**;
- unresolved unknown: **0**.

One versioned scope-review override resolves `2012-0088` because native text extraction is column-garbled but visual source review of page 1 clearly identifies Airbus as Design Approval Holder. This changes scope status only, never source/gold/content text.

## Final clean locked-test result

The parser was frozen before the test labels were scored.

Nominal test count: 20.
Primary clean count after two holder-scope exclusions plus disclosed `2024-0038` leakage: **17**.

| Metric | Result |
|---|---:|
| Prediction coverage | 1.0000 |
| Schema validity | 1.0000 |
| Stable metadata macro F1 | **0.9831** |
| Applicability-model F1 | **0.9222** |
| Reference-number F1 | **0.9000** |
| Superseded-AD-number F1 | **0.6667** |
| Reference/lifecycle macro F1 | **0.7833** |

Raw-section result:

- all five raw-section presence F1 values: **1.0000**;
- source containment: **74/74 = 1.0000**;
- contamination detections: **0**.

These structured test mismatches are final test outcomes. They must not be used to retune parser v2.1.6.

## Extraction-stage decision

**PASS.** Extraction is frozen and ready for reproducible local canonical promotion.

The sandbox reproduction proves the evaluation gates, but the official local run should still be regenerated with the versioned CLI so `run_config.json`, extraction/lifecycle manifests, failures, and evaluation outputs are generated in the user's `data_processed/` workspace before promotion.

## QA benchmark v2

```text
evaluation_sets/easa_airbus_ad_qa_50_v2/
```

| Category | Count | Primary layer tested |
|---|---:|---|
| Identity and snapshot lifecycle | 8 | Metadata + retrieval |
| Applicability | 8 | Original applicability passages |
| Required action and compliance | 16 | Original compliance passages |
| Referenced publication | 6 | Metadata + source verification |
| Conditional or multi-passage | 6 | Multi-passage PDF RAG |
| Insufficient/conflict/abstention | 6 | Answer safeguards |
| **Total** | **50** | |

The live QA system must retrieve original PDF chunks; it may not use hidden gold annotations or treat structured JSON as final compliance evidence.

## Retrieval experiment

- **E0:** flat chunks + dense-only retrieval.
- **E4:** section-aware original-PDF chunks + BM25 + dense retrieval + FAISS + RRF + metadata/lifecycle filtering + reranking.

Measure Recall@1/3/5, MRR, nDCG@5, and correct source/page retrieval.

## Unseen evaluation

Five non-gold PDFs remain frozen at:

```text
evaluation_sets/unseen_incoming_5_v1/
```

Keep them outside development indexes until temporary-upload evaluation. Then permanently ingest the same five without retraining and evaluate isolation, duplicate rejection, index updates, lifecycle safeguards, and citations.

## Locking rules

- Do not tune parser v2.1.6 from the clean extraction test.
- Do not use the five unseen PDFs during development.
- Keep immutable gold and nominal split artifacts unchanged.
- Version every material post-freeze methodology change separately.
- Report actual failures, exclusions, unknowns, and abstentions.
