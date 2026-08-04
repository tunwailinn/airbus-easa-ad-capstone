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

The project scope is EU-issued EASA ADs whose Design/Type Approval Holder is Airbus S.A.S., accepting legacy Airbus/Airbus Industrie naming.

For the frozen gold benchmark, `evaluate_extraction.py` derives eligibility from the reviewed gold holder, never from the prediction being scored.

Confirmed development exclusions:

- `2024-0095`: Airbus Defence and Space S.A.;
- `2026-0079`: Lufthansa Technik AG.

Therefore the primary development benchmark count is currently **28**, while nominal membership remains 30.

For the generated 1,804-record corpus, `scope_policy.py` and `audit_corpus_scope.py` apply a separate operational-scope policy:

- accepted Airbus aliases → eligible;
- confirmed external or mixed approval holders → excluded from the strict Airbus-only operational view while the physical record remains preserved;
- missing, malformed or unfamiliar holder text → unknown pending review.

A parser error must never silently shrink the corpus.

### Confirmed test leakage

AD `2024-0038` belongs to the nominal locked test split, but its source PDF was explicitly inspected while diagnosing earlier parser defects. It is no longer an unbiased extraction-test case.

Final clean extraction reporting must retain the nominal split unchanged, disclose all scope/leakage exclusions, never substitute a development case, and never use clean test labels for subsequent parser tuning.

## Extraction evaluator v3.1.5

The primary evaluator remains `full_corpus_pipeline/evaluate_extraction.py`.

### Primary stable metadata

Report per-field precision, recall, F1 and record-level exact accuracy for representation-comparable reliable values including:

- AD number, authority, document type, revision/emergency/correction state;
- Design/Type Approval Holder;
- subject, issue/effective date and ATA codes;
- manufacturer;
- EASA/legacy TCDS identifiers;
- Foreign AD status; and
- detailed applicability model identifiers.

Report `stable_metadata_macro_f1` across these primary fields.

### Secondary catalogue normalization

Publication-header model identifiers and aircraft-family labels remain secondary under `secondary_taxonomy_macro_f1` because a header may print only a broad family while reviewed annotations expand variants.

Detailed `applicability.models` remains primary.

### Reference and lifecycle identifiers

Report:

- `reference_number_f1`;
- `superseded_ad_number_f1`; and
- `reference_lifecycle_macro_f1`.

Reference identifiers are extracted from the printed reference section. Precision is preferred over speculative recall expansion.

### Raw difficult sections

For Definitions, Reason, Required Actions/Compliance, printed reference wording and Remarks, evaluate:

- actual source-heading presence;
- corresponding parser-section presence;
- source-text containment; and
- page-furniture/status contamination.

When the document-text cache is available, source-heading presence is authoritative for raw-section expectation. Exact semantic overlap with the content projection is not a primary metric; `legacy_projection_overlap` remains diagnostic only.

## Established v2.1.5 development result

The regenerated v2.1.5 development run achieved:

- prediction coverage: **1.000**;
- schema validity: **1.000**;
- stable metadata macro F1: **0.9671**;
- applicability-model F1: **0.9565**;
- reference-number F1: **0.8065**;
- superseded-AD-number F1: **0.9000**;
- raw-section presence F1: **1.000** for all five difficult-section types;
- raw-section source containment: **130/130 = 1.000**; and
- detected raw-section contamination: **0**.

Therefore v2.1.6 is not allowed to redesign raw difficult-section extraction. It is a narrow development hardening pass for catalogue/scope formats only.

The v2.1.5 scope audit (`1765 eligible / 17 excluded / 22 unknown`) is diagnostic, not final; several unknowns were shown by source review to be parser-format misses.

## Development-reference audit

Run before using development scores:

```bash
.venv/bin/python -m full_corpus_pipeline.audit_development_reference \
  --output data_processed/runs/local-content-development-1804-v2.1.6/development_reference_audit.json
```

The immutable release remains 30 nominal / 28 primary eligible development members unless a new formally versioned gold release is created.

## Full generated-corpus scope audit

```bash
.venv/bin/python -m full_corpus_pipeline.audit_corpus_scope \
  data_processed/runs/local-content-development-1804-v2.1.6/records \
  --output data_processed/runs/local-content-development-1804-v2.1.6/corpus_scope_audit.json
```

Use the regenerated v2.1.6 result for scope governance. Do not silently delete excluded or unknown records from the physical inventory. Confirmed mixed/external holders may be omitted only from the strict Airbus-only operational view. Resolve or explicitly document every remaining unknown before freezing that operational count.

## Development evaluation

```bash
.venv/bin/python -m full_corpus_pipeline.evaluate_extraction \
  data_processed/runs/local-content-development-1804-v2.1.6/records \
  --output data_processed/runs/local-content-development-1804-v2.1.6/evaluation_development_v3.1.5.json \
  --split development
```

### v2.1.6 freeze gate

Before touching the locked test, require:

- 1,804 requested / 1,804 successful / zero extraction failures;
- 100% prediction coverage and schema validity on the scored development set;
- raw difficult-section presence/containment/contamination performance remains at the established v2.1.5 level;
- doubled-colon and legacy Type Approval Holder formats are recovered;
- consecutive multi-ATA subjects preserve every printed ATA chapter;
- revision chains do not create false direct supersedure edges;
- no parser-garbage values are classified as confirmed out-of-scope holders;
- every remaining scope unknown is individually reviewed/documented; and
- representative development source-PDF spot checks pass.

If a new genuine defect remains at this point, do not open clean locked-test content to tune it.

## Final clean extraction evaluation

After development behavior is frozen, run the test split once:

```bash
.venv/bin/python -m full_corpus_pipeline.evaluate_extraction \
  data_processed/runs/local-content-development-1804-v2.1.6/records \
  --output data_processed/runs/local-content-development-1804-v2.1.6/evaluation_test_clean_v3.1.5.json \
  --split test
```

Use the generated report's actual `record_count` after disclosed scope/leakage exclusions. Do not tune parser rules after viewing clean test results; any remaining failures are reported as final test outcomes.

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

Measure correct AD/page retrieval, answer correctness, preservation of conditions/alternatives/intervals/terminating effects, page-citation correctness, abstention accuracy, and unsupported-claim rate.

## Retrieval experiment

- **E0:** flat chunks with dense-only retrieval.
- **E4:** section-aware original-PDF chunks, BM25, local embeddings, FAISS, RRF, metadata/lifecycle filtering, and reranking.

Measure Recall@1/3/5, MRR, nDCG@5, and correct-source/page retrieval.

## Unseen evaluation

Five non-gold PDFs from five distinct families remain frozen at:

```text
evaluation_sets/unseen_incoming_5_v1/
```

They remain excluded from development until temporary-upload evaluation, then are permanently ingested without retraining. Evaluate session isolation, clearing, citations, duplicate rejection, index updates, lifecycle safeguards, and ingestion correctness.

## Locking rules

- Use only scope-eligible development references for extraction-rule tuning.
- Do not add new locked-test content to parser regression fixtures.
- Exclude known leaked test cases from clean final scoring and disclose them.
- Do not use the five unseen PDFs during development.
- Keep immutable gold and nominal split artifacts unchanged.
- Version every material parser/evaluator change and regenerate rather than editing generated records in place.
- Report actual failed, excluded, unknown-scope, and abstained cases.
