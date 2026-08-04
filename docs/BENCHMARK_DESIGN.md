# Benchmark Design v3.1

## Evaluation principle

Evaluate the two application layers separately:

- deterministic extraction measures reliable structured metadata plus faithful preservation of raw AD sections;
- retrieval/QA measures evidence selection and interpretation from original PDF passages.

Complex compliance questions are not expected to be answerable from structured fields alone.

## Extraction benchmark

Immutable audit source:

```text
gold_releases/easa_airbus_ad_gold_v2/
```

Active derived content dataset:

```text
evaluation_sets/easa_airbus_ad_content_gold_50_v2/
```

Frozen nominal split:

- development: 30 records;
- locked test: 20 records;
- grouping key: `base_ad_number`;
- seed: 42.

Primary development count after holder-scope exclusions: **28**.
Primary clean-test count after two holder-scope exclusions plus disclosed `2024-0038` leakage: **17**.

Active/frozen parser: **`content-local-v2.1.6`**.
Active evaluator: **`content-eval-v3.1.5`**.

Final development result:

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
- source containment: **130/130**;
- contamination: **0**.

Final clean locked-test result:

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
- source containment: **74/74**;
- contamination: **0**.

These extraction-test outcomes are final and must not be used to retune parser v2.1.6.

## Operational scope

Final development view:

- physical/generated records: **1,804**;
- strict Airbus-only eligible: **1,786**;
- retained external/mixed-holder records: **18**;
- unresolved unknown: **0**.

Scope filtering never deletes physical records.

## Verified RAG source layer

The retrieval benchmark uses only verified original-PDF page text from:

```text
data_processed/page_text_v1_1/operational_airbus/
```

Final source-layer gate:

- page-text version: **`page-text-v1.1`**;
- selected/successful documents: **1,786 / 1,786**;
- total pages: **6,002**;
- failures: **0**;
- native weak pages: **1**;
- reviewed visual override count: **1** (`2011-0006`, page 3);
- unresolved weak/OCR pages: **0**;
- `ready_for_indexing`: **true**.

The five frozen unseen PDFs remain outside this development retrieval corpus.

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

The live QA system must retrieve original PDF chunks. It may not use hidden gold annotations as live evidence or treat structured JSON as final compliance evidence.

## Frozen retrieval comparison

The initial thesis retrieval comparison is now frozen before observing locked-benchmark scores.

### Shared conditions

Both E0 and E4 use:

- the same **1,786-document** `retrieval_manifest.csv`;
- verified **page-text v1.1**;
- the same dense model: `sentence-transformers/all-MiniLM-L6-v2`;
- FAISS inner-product dense indexing;
- top-5 final retrieval evaluation;
- the same answerable locked QA question membership.

Do not tune chunk sizes, embedding model, candidate depth, fusion constant, or reranker after observing locked retrieval results. Any future exploratory variant must be labeled a new experiment and not replace the frozen E0/E4 result.

### E0 — dense-only baseline

- flat page chunks;
- nominal chunk size: **350 tokens**;
- sentence-transformer embeddings;
- FAISS;
- ranking path: **dense only**.

The implementation may contain auxiliary sparse files because the shared index class writes them, but E0 evaluation must call the dense-only search path.

### E4 — proposed section-aware hybrid system

- section-aware chunks;
- target chunk range: **250–450 tokens**;
- SQLite FTS5/BM25;
- same dense embeddings as E0;
- FAISS;
- reciprocal-rank fusion;
- candidate depth: **20 per sparse/dense path**;
- local cross-encoder reranker: `cross-encoder/ms-marco-MiniLM-L-6-v2`;
- metadata/lifecycle controls when applicable.

For the frozen thesis measurement, reranker failure must abort evaluation. Lexical reranking fallback is not permitted.

## Retrieval metrics

For answerable QA questions, report:

- Recall@1;
- Recall@3;
- Recall@5;
- MRR;
- nDCG@5;
- correct source at 1 and 5;
- correct source + reference page at 1 and 5;
- paired E0-vs-E4 rank wins/losses/ties.

A relevant hit requires both:

1. the correct target AD; and
2. a retrieved chunk whose page range contains at least one locked reference page.

## Frozen implementation

Build:

```bash
.venv/bin/python -m full_corpus_pipeline.build_retrieval_experiments \
  --page-text-root data_processed/page_text_v1_1/operational_airbus \
  --output-root data_processed/indexes/rag_v1 \
  --experiment all
```

Evaluate:

```bash
.venv/bin/python -m full_corpus_pipeline.evaluate_retrieval_experiments \
  --index-root data_processed/indexes/rag_v1 \
  --output data_processed/indexes/rag_v1/retrieval_comparison.json
```

The build must report `sentence_transformers` and `faiss_index_flat_ip`. Frozen thesis measurements may not use the hashing or numpy-only fallbacks.

## Unseen evaluation

Five non-gold PDFs remain frozen at:

```text
evaluation_sets/unseen_incoming_5_v1/
```

Keep them outside development indexes until temporary-upload evaluation. Then permanently ingest the same five without retraining and evaluate isolation, duplicate rejection, index updates, lifecycle safeguards, and citations.

## Locking rules

- Do not tune parser v2.1.6 from the clean extraction test.
- Do not tune frozen E0/E4 from locked retrieval results.
- Do not use the five unseen PDFs during development.
- Keep immutable gold and nominal split artifacts unchanged.
- Version every material post-freeze methodology change separately.
- Report actual failures, exclusions, unknowns, abstentions, and fallback/runtime failures.
