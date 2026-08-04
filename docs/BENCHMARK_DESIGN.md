# Benchmark Design v3.1

## Evaluation principle

The two application layers are evaluated separately:

- deterministic content extraction measures reliable structured metadata plus faithful preservation of raw AD sections; and
- QA measures retrieval and interpretation from original PDF passages.

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

The immutable annotations contain independently reviewed structured values and exact source evidence. The derived content projection intentionally compresses difficult content into reviewed semantic units, while the live deterministic parser preserves complete printed PDF sections. These two representations must not be scored as if their raw strings were expected to be identical.

### Frozen nominal split

- Nominal development set: 30 records.
- Nominal locked test set: 20 records.
- Grouping key: `base_ad_number`.
- Seed: 42.

The frozen split artifact remains unchanged for traceability. Primary evaluation operates on the subset that is both project-scope eligible and, for the test split, still genuinely unseen.

## Benchmark eligibility

### Project-scope eligibility

The project scope is EU-issued EASA ADs whose Design/Type Approval Holder is Airbus S.A.S., accepting legacy holder naming such as `Airbus` and `Airbus Industrie` where applicable.

`evaluate_extraction.py` derives scope eligibility from the reviewed gold `design_approval_holder` value. Clearly different organizations or Airbus divisions outside Airbus S.A.S. are retained in the immutable audit release but excluded from primary extraction scoring.

Confirmed examples:

- development AD `2026-0079`: `LUFTHANSA TECHNIK AG` — excluded from primary development scoring;
- test AD `2021-0286`: `Airbus Defence and Space S.A.` — excluded from primary test scoring.

Unknown/missing holder values are surfaced separately as `scope_unknown`; they are never silently treated as confirmed scope matches.

### Confirmed test leakage

AD `2024-0038` belongs to the nominal locked test split, but its source PDF was explicitly inspected while diagnosing and fixing parser v2.1.4. It is no longer an unbiased test case.

Final clean extraction reporting must:

- retain the original nominal 30/20 split artifact unchanged;
- exclude out-of-scope holder cases from primary scoring;
- exclude `2024-0038` from primary locked-test scoring;
- disclose every exclusion and reason; and
- never substitute a development case into the test set.

`--include-scope-excluded` and `--include-contaminated` exist only for diagnostics and must not be used for the primary thesis result.

## Extraction evaluation v3.1.4

The primary evaluator is `full_corpus_pipeline/evaluate_extraction.py`.

### Primary stable-metadata metrics

Report per-field precision, recall, F1, and record-level exact accuracy for comparable reliable values such as:

- AD number, authority, document type, revision/emergency/correction state;
- design approval holder;
- subject, issue date, effective date, and ATA codes;
- manufacturer;
- publication model identifiers;
- EASA TCDS identifiers;
- Foreign AD status; and
- applicability model identifiers.

Also report `stable_metadata_macro_f1` across these comparable stable fields.

The evaluator applies only representation-safe normalization, for example:

- `airworthiness_directive` versus `Airworthiness Directive`;
- `Manufacturer(s): Airbus` versus `Airbus`;
- an `ATA 53 –` prefix versus the same subject without that prefix;
- `Foreign AD: Not applicable` versus `Not applicable`;
- model identifiers embedded in a broader gold phrase; and
- an EASA TCDS identifier embedded in a combined historical-TCDS string.

It does not forgive arbitrary semantic differences.

### Secondary taxonomy metric

Aircraft-family labels are reported separately as `secondary_taxonomy_macro_f1` because the reviewed gold taxonomy and the parser's broad family grouping can use different abstraction levels. This metric remains visible but is not mixed into the primary stable-metadata macro F1.

### Reference and lifecycle identifiers

Report publication-reference number F1 and superseded-AD-number F1 separately, together with `reference_lifecycle_macro_f1`.

This prevents optional title/revision/date representation differences from obscuring whether the parser found the identifiers needed for retrieval and lifecycle support.

### Raw difficult sections

For Definitions, Reason, Required Actions/Compliance, reference wording, and Remarks, evaluate:

- expected-section presence;
- source-text containment where the frozen document-text cache is available; and
- contamination by repeated page furniture/status watermarks.

Do **not** use exact string overlap between the live raw section and the semantic gold projection as the primary score. The gold may contain reviewed definition pairs or individual action units while the parser intentionally preserves the complete printed section.

The previous flatten-and-set projection-overlap metric is retained only as `legacy_projection_overlap` for continuity and is explicitly marked non-primary.

## Development-reference audit

Before using development scores to modify the parser, run:

```bash
.venv/bin/python -m full_corpus_pipeline.audit_development_reference \
  --output data_processed/runs/local-content-development-1804-v2.1.4/development_reference_audit.json
```

The audit opens only the nominal 30 development references. It checks:

- frozen annotation and derived-record hashes;
- approved release status and independent human-review provenance;
- deterministic reprojection to the content schema;
- substantive field-assertion acceptance;
- source-document identifiers and hashes;
- evidence-span page/quote integrity;
- auxiliary evidence-quote containment in the frozen document-text cache when available; and
- project-scope eligibility from the reviewed Design Approval Holder.

The report retains the nominal count and separately reports the eligible count and exclusions. It deliberately does not open test compliance labels.

## Development evaluation

After the audit passes, run:

```bash
.venv/bin/python -m full_corpus_pipeline.evaluate_extraction \
  data_processed/runs/local-content-development-1804-v2.1.4/records \
  --output data_processed/runs/local-content-development-1804-v2.1.4/evaluation_development_v3.1.4.json \
  --split development
```

For the current nominal development split, AD `2026-0079` is expected to appear under `scope_exclusions`; the primary `record_count` is therefore expected to be 29 unless another holder is classified as out of scope or unknown.

Development results may be used to diagnose extraction rules.

## Final clean extraction evaluation

After development is frozen, run the test split once:

```bash
.venv/bin/python -m full_corpus_pipeline.evaluate_extraction \
  data_processed/runs/local-content-development-1804-v2.1.4/records \
  --output data_processed/runs/local-content-development-1804-v2.1.4/evaluation_test_clean_v3.1.4.json \
  --split test
```

The evaluator will report:

- `nominal_split_count`;
- `record_count` after exclusions;
- `scope_exclusions`;
- `scope_unknown`; and
- `contamination_exclusions`.

Two test exclusions are already known: `2021-0286` for holder scope and `2024-0038` for parser-tuning leakage. The actual clean test count must be taken from the generated report rather than assumed in advance.

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

The immutable audit annotations may be used privately to construct reference answers and source pages. The live QA system must retrieve original PDF chunks; it may not use hidden gold annotations or treat structured JSON fields as final compliance evidence.

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

They are excluded from development, tested temporarily, then permanently ingested to reach 1,809 records. Test isolation, clearing, citations, duplicate rejection, index updates, lifecycle safeguards, and absence of retraining.

## Locking rules

- Use only scope-eligible development references for extraction-rule tuning.
- Exclude known leaked test cases from clean final scoring and disclose them.
- Do not use the remaining clean test labels for tuning.
- Do not use the five unseen PDFs during development.
- Keep immutable gold and nominal split artifacts unchanged; implement eligibility/exclusion in versioned evaluation logic.
- Report actual results, including failed, excluded, unknown-scope, and abstained cases.
