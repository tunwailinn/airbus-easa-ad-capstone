# Benchmark Design v3.2

## Evaluation principle

Evaluate the application layers separately and preserve test-set boundaries:

- deterministic extraction measures reliable structured metadata plus faithful raw-section preservation;
- retrieval measures source/page evidence selection;
- hosted QA measures interpretation and grounding given retrieved evidence;
- unseen ingestion is evaluated separately from retrieval development.

Complex compliance questions are not expected to be answerable from structured fields alone.

## Extraction benchmark — FINAL / FROZEN

Immutable audit source:

```text
gold_releases/easa_airbus_ad_gold_v2/
```

Derived content dataset:

```text
evaluation_sets/easa_airbus_ad_content_gold_50_v2/
```

Frozen family-level split:

- development: 30 records;
- locked test: 20 records;
- seed: 42.

Primary development count after holder-scope exclusions: **28**.  
Primary clean-test count after two holder-scope exclusions plus disclosed `2024-0038` leakage: **17**.

Parser: **`content-local-v2.1.6`**.  
Evaluator: **`content-eval-v3.1.5`**.

Final development:

| Metric | Result |
|---|---:|
| Prediction coverage | 1.0000 |
| Schema validity | 1.0000 |
| Stable metadata macro F1 | **0.9948** |
| Applicability-model F1 | **0.9929** |
| Reference-number F1 | **0.8065** |
| Superseded-AD-number F1 | **1.0000** |

Final clean locked test:

| Metric | Result |
|---|---:|
| Prediction coverage | 1.0000 |
| Schema validity | 1.0000 |
| Stable metadata macro F1 | **0.9831** |
| Applicability-model F1 | **0.9222** |
| Reference-number F1 | **0.9000** |
| Superseded-AD-number F1 | **0.6667** |

All five difficult raw-section presence F1 values are **1.0000** in development and clean test. Source containment is 130/130 development and 74/74 test, with zero detected contamination.

These results are final and must not be used to retune parser v2.1.6.

## Operational retrieval source

Verified source:

```text
data_processed/page_text_v1_1/operational_airbus/
```

- strict Airbus-only development documents: **1,786**;
- pages: **6,002**;
- failures: **0**;
- unresolved weak/OCR pages: **0**;
- reviewed visual override: AD `2011-0006`, page 3;
- `ready_for_indexing=true`.

The five frozen unseen PDFs remain outside development retrieval indexes.

## QA-v2 — frozen E0/E4 benchmark

```text
evaluation_sets/easa_airbus_ad_qa_50_v2/
```

| Category | Count |
|---|---:|
| Identity/snapshot lifecycle | 8 |
| Applicability | 8 |
| Required action/compliance | 16 |
| Referenced publication | 6 |
| Conditional/multi-passage | 6 |
| Insufficient/conflict/abstention | 6 |
| **Total** | **50** |

The retrieval evaluator uses the 44 answerable questions. The six abstention questions are reserved for full QA safeguards.

### Frozen E0/E4 configuration

Both use:

- the same 1,786-document corpus;
- page-text v1.1;
- `sentence-transformers/all-MiniLM-L6-v2`;
- FAISS `IndexFlatIP`.

E0:

- 9,394 flat chunks;
- max 350 whitespace units;
- dense-only ranking.

E4:

- 12,634 section-aware chunks;
- max 450 whitespace units;
- SQLite FTS5/BM25 + dense + FAISS + RRF;
- candidate depth 20 per sparse/dense path;
- `cross-encoder/ms-marco-MiniLM-L-6-v2` reranker.

Frozen build:

```text
data_processed/indexes/rag_v1_2/
```

Evaluator: **`retrieval-eval-v1.3`**.

### Final E0/E4 results

E0:

- Recall@1/3/5: **0.0000 / 0.0000 / 0.0000**;
- MRR: **0.0000**;
- nDCG@5: **0.0000**;
- correct-source@1/@5: **0.0000 / 0.0000**;
- correct-source+page@1/@5: **0.0000 / 0.0000**.

E4:

- Recall@1: **0.2500**;
- Recall@3: **0.3636**;
- Recall@5: **0.4091**;
- MRR: **0.3106**;
- nDCG@5: **0.3353**;
- correct-source@1: **0.2727**;
- correct-source@5: **0.5000**;
- correct-source+page@1: **0.2500**;
- correct-source+page@5: **0.4091**;
- paired: E4 better 18 / E0 better 0 / ties 26.

Post-evaluation plumbing diagnostics passed:

- FAISS/chunk alignment: 20/20 sampled rows exact for E0 and E4;
- fresh-vs-stored embedding cosine ≈1.0;
- all benchmark target ADs present in both indexes;
- E0 dense correct-source@20: 0/44;
- E4 dense correct-source@20: 0/44;
- E4 BM25 correct-source+page@20: **40/44 (0.9091)**.

Interpretation: E4's gain is primarily from lexical/section-aware hybrid retrieval, not the MiniLM dense branch. QA-v2 remains frozen and is not reused for E5 tuning.

## E5 benchmark v1 — NEW development + untouched final test

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/
```

Full methodology: `docs/E5_ENGINEERING_AWARE_RETRIEVAL.md`.

### Family isolation

Use 40 new base AD families selected deterministically from the verified 1,786-document corpus:

- 24 development families;
- 16 final-test families;
- seed `20260805`;
- stratified by publication era;
- all eight QA-v2 target families excluded;
- five unseen-ingestion families remain excluded.

Generate/freeze membership locally:

```bash
.venv/bin/python -m full_corpus_pipeline.prepare_e5_benchmark_families
```

### E5 development — 60 questions

| Category | Count |
|---|---:|
| Identity/lifecycle | 8 |
| Applicability | 10 |
| Required action/compliance | 20 |
| Referenced publication | 8 |
| Conditional/multi-passage | 8 |
| Insufficient/conflict/abstention | 6 |
| **Total** | **60** |

Query modes:

- known-document: 36;
- identifier-free discovery: 18;
- abstention/conflict: 6.

These questions may be used for E5 configuration/model selection.

### E5 final — 40 questions

| Category | Count |
|---|---:|
| Identity/lifecycle | 5 |
| Applicability | 7 |
| Required action/compliance | 14 |
| Referenced publication | 5 |
| Conditional/multi-passage | 5 |
| Insufficient/conflict/abstention | 4 |
| **Total** | **40** |

Query modes:

- known-document: 24;
- identifier-free discovery: 12;
- abstention/conflict: 4.

The final set remains unopened until E5 retrieval configuration and hosted-QA prompt/model/settings are frozen.

## E5 retrieval metrics

Report separately by query mode.

- document-route accuracy;
- correct-source@1/5/10;
- correct-source+page Recall@1/3/5/10;
- MRR;
- nDCG@5;
- multi-passage coverage;
- evidence-pack support status.

Known-document queries primarily test page/passage selection because the document identity is supplied by the user. Discovery queries test both document identification and page selection.

## Hosted QA evaluation

Hosted generation is downstream of retrieval and never receives hidden gold.

Initial configured model:

```text
DeepSeek V4 Pro / deepseek-v4-pro
```

Provider integration remains configurable/OpenAI-compatible.

The model receives stable evidence IDs and retrieved passages. It returns evidence IDs, not page citations. Application code validates evidence IDs and resolves citations from retrieval metadata.

Run two QA conditions with the same frozen prompt/model settings:

1. **end-to-end E5 evidence** — real retrieved evidence pack;
2. **oracle evidence** — human-verified reference passages.

This separates retrieval failures from generation failures.

QA metrics:

- answer accuracy;
- condition/exception completeness;
- citation correctness/completeness;
- unsupported-claim rate;
- abstention precision/recall;
- supported-subset answer accuracy;
- oracle-evidence answer accuracy.

## Unseen evaluation

Five non-gold PDFs remain frozen at:

```text
evaluation_sets/unseen_incoming_5_v1/
```

They remain outside E5 development/final benchmark construction. Evaluate temporary-upload QA first, then permanent ingestion without retraining, including isolation, duplicate rejection, index updates, lifecycle safeguards, and citations.

## Locking rules

- Do not retune parser v2.1.6 from extraction test results.
- Do not retune E0/E4 from QA-v2 results.
- QA-v2 may motivate E5 architecture but may not select E5 parameters/models.
- Tune E5 only on the 60-question E5 development set.
- Freeze E5 before opening the 40-question final set.
- Do not use the five unseen PDFs in E5 development/final benchmark construction.
- Keep immutable gold and old benchmark artifacts unchanged.
- Report actual failures, abstentions, runtime failures, and negative results.
