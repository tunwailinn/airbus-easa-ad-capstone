# Benchmark Design v3.1

## Evaluation principle

The application layers are evaluated separately:

- deterministic content extraction measures reliable structured metadata plus faithful preservation of raw AD sections; and
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

The immutable annotations contain independently reviewed structured values and source evidence. The derived content projection intentionally compresses difficult content into reviewed semantic units, while the live deterministic parser preserves complete printed PDF sections. These representations must not be scored as though their raw strings should be identical.

### Frozen nominal split

- Nominal development set: 30 records.
- Nominal locked test set: 20 records.
- Grouping key: `base_ad_number`.
- Seed: 42.

The split artifact remains unchanged for traceability. Primary evaluation operates on the subset that is project-scope eligible and, for the test split, still genuinely unseen.

## Benchmark eligibility

### Project-scope eligibility

The project scope is EU-issued EASA ADs whose Design/Type Approval Holder is Airbus S.A.S., accepting legacy holder naming such as `Airbus` and `Airbus Industrie` where applicable.

`evaluate_extraction.py` derives benchmark eligibility from the reviewed gold `design_approval_holder`, never from the prediction being scored.

Confirmed development exclusions:

- `2024-0095`: Airbus Defence and Space S.A.;
- `2026-0079`: Lufthansa Technik AG.

Therefore the current primary development benchmark count is **28**, while the nominal split remains 30.

Clearly different organizations or Airbus divisions outside Airbus S.A.S. remain in the immutable audit release but are excluded from primary scoring and disclosed. Unknown/missing reviewed holder values are surfaced separately as `scope_unknown`; they are never silently treated as confirmed scope matches.

For the generated 1,804-record corpus-scope audit, malformed machine-extracted holder values are classified as `unknown`, not `excluded`. A parser boundary error must not silently reduce the operational corpus.

### Confirmed test leakage

AD `2024-0038` belongs to the nominal locked test split, but its source PDF was explicitly inspected while diagnosing parser defects. It is no longer an unbiased extraction-test case.

Final clean extraction reporting must:

- retain the nominal 30/20 split artifact unchanged;
- exclude reviewed out-of-scope holder cases from primary scoring;
- exclude `2024-0038` from primary locked-test scoring;
- disclose every exclusion and reason; and
- never substitute a development case into the test set.

`--include-scope-excluded` and `--include-contaminated` are diagnostic-only switches and must not be used for the primary thesis result.

## Extraction evaluation v3.1.5

The primary evaluator is `full_corpus_pipeline/evaluate_extraction.py`.

### Primary stable-metadata metrics

Report per-field precision, recall, F1, and record-level exact accuracy for representation-comparable reliable values:

- AD number, authority, document type, revision/emergency/correction state;
- Design/Type Approval Holder;
- subject, issue date, effective date, and ATA codes;
- manufacturer;
- EASA/legacy TCDS identifiers;
- Foreign AD status; and
- detailed applicability model identifiers.

Also report `stable_metadata_macro_f1` across these primary stable fields.

The evaluator applies only representation-safe normalization, for example:

- `airworthiness_directive` versus `Airworthiness Directive`;
- `Manufacturer(s): Airbus` versus `Airbus`;
- an `ATA 53 –` prefix versus the same subject without that prefix;
- `Foreign AD: Not applicable` versus `Not applicable`;
- model identifiers embedded in a broader applicability phrase; and
- an EASA or France TCDS identifier embedded in a combined historical-TCDS string.

It does not forgive arbitrary semantic differences.

### Secondary catalogue normalization

Report publication-header model identifiers and aircraft-family labels separately under `secondary_taxonomy_macro_f1`.

This is secondary because:

- an AD header may print only `A350 aeroplanes` while the reviewed annotation expands individual certified models; and
- the parser may group A318/A319/A320/A321 into `A320 family` while reviewed labels enumerate families separately.

Detailed `applicability.models` remains a primary field because the applicability section is the correct location for model-specific scope.

### Reference and lifecycle identifiers

Report:

- `reference_number_f1`;
- `superseded_ad_number_f1`; and
- `reference_lifecycle_macro_f1`.

Reference identifiers are extracted deterministically from the printed reference-publication section. The metric focuses on identifiers rather than optional title/revision/date representation.

### Raw difficult sections

For Definitions, Reason, Required Actions/Compliance, printed reference wording, and Remarks, evaluate:

- whether the **source document actually contains the section heading**;
- whether the parser preserves a corresponding section when printed;
- whether the extracted section is contained in the cleaned source text; and
- whether repeated page furniture/status watermarks contaminate the preserved section.

When `corpus_extracted_text.parquet` is available, source-heading presence is authoritative for raw-section expectation. This avoids two old errors:

1. treating a semantic gold projection as proof that an identically represented raw section exists; and
2. assigning `referenced_publications_text` a meaningless zero merely because the projection has no raw-equivalent field.

If source text is unavailable, raw reference wording is reported as unscorable rather than as F1=0.

Do **not** use exact string overlap between the live raw section and semantic gold units as the primary score. `legacy_projection_overlap` remains diagnostic only.

## Development-reference audit

Run before using development scores to modify the parser:

```bash
.venv/bin/python -m full_corpus_pipeline.audit_development_reference \
  --output data_processed/runs/local-content-development-1804-v2.1.5/development_reference_audit.json
```

The audit opens only the nominal 30 development references. It checks:

- frozen annotation and derived-record hashes;
- approved release status and independent human-review provenance;
- deterministic reprojection to the content schema;
- substantive field-assertion acceptance;
- source-document identifiers and hashes;
- evidence-span page/quote integrity;
- auxiliary evidence-quote containment in the document-text cache when available; and
- project-scope eligibility from the reviewed holder.

Current expected nominal/eligible counts are 30/28 unless the immutable audit source itself changes through a formally versioned release. The existing immutable release is not edited to remove the two scope exclusions.

## Full generated-corpus scope audit

After every material parser change, scan the complete generated development run:

```bash
.venv/bin/python -m full_corpus_pipeline.audit_corpus_scope \
  data_processed/runs/local-content-development-1804-v2.1.5/records \
  --output data_processed/runs/local-content-development-1804-v2.1.5/corpus_scope_audit.json
```

The v2.1.4 result `1729 eligible / 59 excluded / 16 unknown` is explicitly **not a final corpus count** because many `excluded` holder strings were parser boundary failures such as Type/Model text. Use the v2.1.5 regenerated scope report for the next corpus-governance decision.

A scope report may contain:

- `eligible`: holder confidently maps to Airbus S.A.S./legacy Airbus;
- `excluded`: holder confidently names another organization/division; and
- `unknown`: holder missing or malformed and requiring parser/governance review.

Do not silently delete excluded/unknown records from the immutable source inventory.

## Development evaluation

After regenerating parser v2.1.5:

```bash
.venv/bin/python -m full_corpus_pipeline.evaluate_extraction \
  data_processed/runs/local-content-development-1804-v2.1.5/records \
  --output data_processed/runs/local-content-development-1804-v2.1.5/evaluation_development_v3.1.5.json \
  --split development
```

Development results may be used to diagnose extraction rules only on project-scope-eligible development records.

Before freezing extraction behavior, require at minimum:

- full prediction coverage and schema validity;
- no unexpected missing printed Required Actions/Compliance sections;
- no material repeated page furniture in preserved raw sections;
- stable DAH boundaries across old/new layouts;
- acceptable/documented reference and lifecycle identifier performance; and
- representative source-PDF spot checks.

## Final clean extraction evaluation

After parser/evaluator behavior is frozen, run the test split once:

```bash
.venv/bin/python -m full_corpus_pipeline.evaluate_extraction \
  data_processed/runs/local-content-development-1804-v2.1.5/records \
  --output data_processed/runs/local-content-development-1804-v2.1.5/evaluation_test_clean_v3.1.5.json \
  --split test
```

The evaluator reports:

- `nominal_split_count`;
- actual `record_count` after scope/leakage exclusions;
- `scope_exclusions`;
- `scope_unknown`; and
- `contamination_exclusions`.

The final clean test count must be taken from the generated report, not assumed in advance. Do not use clean test labels to tune parser v2.1.5 or later versions.

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

The live QA system must retrieve original PDF chunks; it may not use hidden gold annotations or treat structured JSON fields as final compliance evidence.

### QA grading

Measure:

- correct AD and page retrieval;
- answer correctness;
- preservation of conditions, alternatives, intervals, and terminating effects;
- page-citation correctness;
- abstention accuracy; and
- unsupported-claim rate.

## Retrieval experiment

- **E0:** flat chunks with dense-only retrieval.
- **E4:** section-aware original-PDF chunks, BM25, local embeddings, FAISS, RRF, metadata/lifecycle filtering, and reranking.

Measure Recall@1/3/5, MRR, nDCG@5, and correct-source/page retrieval.

## Unseen evaluation

Five non-gold PDFs from five distinct families remain frozen at:

```text
evaluation_sets/unseen_incoming_5_v1/
```

They are excluded from development, tested temporarily, then permanently ingested without retraining. Evaluate session isolation, clearing, citations, duplicate rejection, index updates, lifecycle safeguards, and ingestion correctness.

## Locking rules

- Use only scope-eligible development references for extraction-rule tuning.
- Do not add new locked-test content to parser regression fixtures.
- Exclude known leaked test cases from clean final scoring and disclose them.
- Do not use the five unseen PDFs during development.
- Keep immutable gold and nominal split artifacts unchanged; implement eligibility/exclusion in versioned evaluation logic.
- Version every material parser/evaluator change and regenerate rather than editing generated records in place.
- Report actual results, including failed, excluded, unknown-scope, and abstained cases.
