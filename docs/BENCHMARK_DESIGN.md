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

### Frozen split

- Nominal development set: 30 records.
- Nominal locked test set: 20 records.
- Grouping key: `base_ad_number`.
- Seed: 42.

The frozen split itself remains unchanged for traceability.

### Confirmed test-set contamination

AD `2024-0038` belongs to the nominal locked test set, but its source PDF was explicitly inspected while diagnosing and fixing parser v2.1.4. It is therefore no longer an unbiased test case.

Final clean extraction reporting must:

- retain the original 30/20 split artifact unchanged;
- exclude `2024-0038` from the primary locked-test score;
- report the clean locked-test sample as **n = 19**;
- disclose the exclusion and reason; and
- never replace it with one of the 30 development records.

`evaluate_extraction.py` excludes this case from test scoring by default. `--include-contaminated` is diagnostic only and must not be used for the primary thesis result.

## Extraction evaluation v3.1.2

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

Aircraft-family labels are reported separately as `secondary_taxonomy_macro_f1` because the reviewed gold taxonomy and the parser's broad family grouping can legitimately use different abstraction levels. This metric remains visible but is not mixed into the primary stable-metadata macro F1.

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

The audit opens only the 30 development references. It checks:

- frozen annotation and derived-record hashes;
- approved release status and independent human-review provenance;
- deterministic reprojection to the content schema;
- substantive field-assertion acceptance;
- source-document identifiers and hashes;
- evidence-span page/quote integrity; and
- auxiliary evidence-quote containment in the frozen document-text cache when available.

It deliberately does not open the locked test labels.

## Development evaluation

After the audit passes, run:

```bash
.venv/bin/python -m full_corpus_pipeline.evaluate_extraction \
  data_processed/runs/local-content-development-1804-v2.1.4/records \
  --output data_processed/runs/local-content-development-1804-v2.1.4/evaluation_development_v3.1.2.json \
  --split development
```

Development results may be used to diagnose extraction rules.

## Final clean extraction evaluation

After development is frozen, run the test split once:

```bash
.venv/bin/python -m full_corpus_pipeline.evaluate_extraction \
  data_processed/runs/local-content-development-1804-v2.1.4/records \
  --output data_processed/runs/local-content-development-1804-v2.1.4/evaluation_test_clean_v3.1.2.json \
  --split test
```

The report should show `nominal_split_count: 20`, `record_count: 19`, and a contamination exclusion for AD `2024-0038`.

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

- Use only the 30 development records for extraction-rule tuning.
- Exclude known leaked test cases from clean final scoring and disclose them.
- Do not use the remaining clean test labels for tuning.
- Do not use the five unseen PDFs during development.
- Version changed schemas/evaluators instead of overwriting immutable audit sources.
- Report actual results, including failed, excluded, and abstained cases.
