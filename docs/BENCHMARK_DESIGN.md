# Benchmark Design

Last updated: 14 August 2026

## Evaluation principle

Evaluate the application layers separately and preserve test-set boundaries:

- **Layer A extraction** measures reliable structured metadata plus faithful source-derived raw-section preservation;
- **Layer B retrieval** measures source/page evidence selection;
- **Layer C hosted QA** measures interpretation, grounding, completeness, citation use, and abstention given supplied evidence;
- **oracle/reference evidence** is diagnostic only and separates retrieval/evidence-selection effects from generation behavior;
- **unseen ingestion** is evaluated separately from E5 development/final benchmarking.

Complex compliance questions are not expected to be answerable from structured fields alone. Original PDF passages remain authoritative.

## Corpus boundaries

Frozen physical snapshot:

- **1,809 PDFs**;
- **1,808 base AD families**.

Five frozen unseen PDFs remain excluded from all development and E5 final benchmark construction.

Nominal development extraction:

- **1,804 physical PDFs**.

Strict Airbus-only operational retrieval view:

- **1,786 documents**;
- **6,002 verified pages**;
- **18 external/mixed-holder records** retained physically but excluded from the strict operational view.

## Layer A extraction benchmark — FINAL / FROZEN

Immutable audit source:

```text
gold_releases/easa_airbus_ad_gold_v2/
```

Frozen parser:

```text
content-local-v2.1.6
```

### Development

Primary development count: **28**.

| Metric | Result |
|---|---:|
| Prediction coverage | 1.0000 |
| Schema validity | 1.0000 |
| Stable metadata macro F1 | **0.9948** |
| Applicability-model F1 | **0.9929** |
| Reference-number F1 | **0.8065** |
| Superseded-AD-number F1 | **1.0000** |

All five difficult raw-section presence F1 values are **1.0000**. Source containment is **130/130**, with zero detected contamination.

### Clean locked extraction test

Primary clean-test count: **17** after two holder-scope exclusions plus disclosed `2024-0038` leakage.

| Metric | Result |
|---|---:|
| Prediction coverage | 1.0000 |
| Schema validity | 1.0000 |
| Stable metadata macro F1 | **0.9831** |
| Applicability-model F1 | **0.9222** |
| Reference-number F1 | **0.9000** |
| Superseded-AD-number F1 | **0.6667** |

All five difficult raw-section presence F1 values are **1.0000**. Source containment is **74/74**, with zero detected contamination.

These outcomes are final and must not be used to retune parser v2.1.6.

## Layer B verified source layer

Canonical page-preserving source:

```text
data_processed/page_text_v1_1/operational_airbus/
```

- documents: **1,786 / 1,786 successful**;
- pages: **6,002**;
- failures: **0**;
- unresolved weak/OCR pages: **0**;
- visually reviewed override: AD `2011-0006`, page 3;
- `ready_for_indexing=true`.

The five unseen PDFs remain outside this development retrieval source.

## QA-v2 historical E0/E4 benchmark — FROZEN

```text
evaluation_sets/easa_airbus_ad_qa_50_v2/
```

- 50 locked questions;
- 44 answerable retrieval questions;
- 6 abstention/conflict questions reserved for full QA safeguards.

E0:

- 9,394 flat chunks;
- MiniLM dense-only ranking;
- Recall@5: **0.0000**.

E4:

- 12,634 section-aware chunks;
- 2,924 multi-page chunks;
- SQLite FTS5/BM25 + dense + FAISS + RRF + reranker;
- Recall@5: **0.4091**;
- MRR: **0.3106**;
- nDCG@5: **0.3353**.

Post-evaluation diagnostics showed E4's improvement was primarily lexical/section-aware rather than from the frozen MiniLM dense branch. QA-v2 is historical and is not reused for E5 tuning.

## E5 benchmark v1

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/
```

Family isolation:

- **40 new base AD families**;
- 24 development families;
- 16 final-test families;
- deterministic seed `20260805`;
- stratified by publication era;
- QA-v2 target families excluded;
- five unseen-ingestion families excluded.

## E5 development — 60 questions

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

Only this development set was used for E5 retrieval and hosted-QA configuration decisions.

## E5-D retrieval — SELECTED / FROZEN

Selected stack:

- deterministic known-document routing;
- E5-C BM25 + `Qwen/Qwen3-Embedding-0.6B@97b0c61` candidate generation;
- fixed candidate depth: **20**;
- `Qwen/Qwen3-Reranker-0.6B@e61197e` passage reranker;
- frozen engineering instruction;
- final evidence depth: **5**;
- frozen E4 section chunks.

Development result:

| Metric | E5-D |
|---|---:|
| Recall@1 | **0.7963** |
| Recall@3 | **0.9259** |
| Recall@5 | **0.9630** |
| MRR@5 | **0.8633** |
| nDCG@5 | **0.8884** |
| Correct source@5 | **0.9815** |
| Correct source+page@5 | **0.9630** |
| Candidate source+page recall@20 | **0.9815** |

Query modes:

- known-document Recall@5: **1.0000 (36/36)**;
- discovery Recall@5: **0.8889 (16/18)**;
- routing accuracy: **1.0000**.

Machine-readable freeze:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/retrieval_freeze.json
```

Do not retune retrieval against development misses after this freeze.

## Layer C hosted QA — FROZEN

Hosted generation is downstream of retrieval and never receives hidden gold.

Frozen configuration:

```text
provider: DeepSeek official API
adapter: deepseek-direct-v1.1
model: deepseek-v4-pro
thinking: enabled
reasoning_effort: high
max_tokens: 4096
prompt: e5-hosted-qa-prompt-v1.0-dev
runner: e5-hosted-qa-runner-v1.1
response contract: e5-hosted-qa-contract-v1.0
semantic retry: prohibited
```

The model receives stable evidence IDs and source passages. Application code validates returned evidence IDs and resolves AD/PDF/page/section citations locally.

Hosted-QA freeze:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/hosted_qa_freeze.json
```

## E5 final — 40 questions — COMPLETE / FROZEN

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

The final questions were human reviewed and locked before the primary run.

Final questions SHA-256:

```text
f6b008c1b5d24160cb5718e2d4e91a7e0d323277a531654e4b5c3a33995c9a85
```

### Primary final automatic result

- hosted request success: **40/40 = 100%**;
- answerability/status accuracy: **100%**;
- Recall@1: **0.8333**;
- Recall@3: **0.9722**;
- Recall@5: **35/36 = 97.22%**;
- MRR@5: **0.8981**;
- nDCG@5: **0.9173**;
- correct source+page@5: **97.22%**;
- known-document Recall@5: **24/24 = 100%**;
- discovery Recall@5: **11/12 = 91.67%**;
- reference-page citation hit rate: **97.22%**;
- target-AD citation hit rate: **97.22%**.

### Primary final human semantic result

- passes: **38/40**;
- failures: **2/40**;
- **strict end-to-end semantic accuracy: 95.0%**.

This 95.0% value is authoritative and may not be replaced by post-hoc adjusted scores.

Primary failure attribution:

- `E5F-011`: Layer C answer-selection/completeness failure under retrieved evidence;
- `E5F-021`: Layer B retrieval/candidate-generation failure.

## Oracle/reference-evidence diagnostic — COMPLETE

Run only after preserving the strict primary result.

Oracle evidence policy:

- answerable questions receive source chunks from human-reviewed target AD/reference pages;
- abstention questions retain the exact primary evidence as negative controls;
- same model/prompt/settings as primary;
- no retrieval rerun or retuning;
- diagnostic only.

Original oracle batch:

- 40 selected;
- 39 successful;
- 1 technical/provider failure (`E5F-035`);
- request success rate: **97.5%**;
- answerability/status accuracy on successful requests: **97.44%**;
- reference-page citation hit rate: **100%**;
- target-AD citation hit rate: **100%**.

Attribution findings:

- `E5F-021` becomes correct under oracle evidence → **Layer B retrieval failure confirmed**;
- `E5F-011` becomes correct under focused oracle evidence → primary Layer C failure is more precisely **evidence-selection/completeness sensitivity**;
- `E5F-040`, with unchanged negative-control evidence, changes status from `insufficient_evidence` to `answered` while preserving cautious prose → **Layer C status-calibration/run-to-run variability**.

`E5F-035` exact transport retry:

- original issue: empty DeepSeek JSON final content;
- exact prompt payload SHA preserved: `74ad9826c35d14082c13f15d94a639d017462b0515092c17e0fa4fd42b28892c`;
- retry result: **recovered successfully**;
- original 39-success/1-failure oracle batch remains preserved.

Oracle and transport-retry results must never replace the strict 38/40 primary score.

## Unseen evaluation — NEXT

Five non-gold PDFs remain frozen at:

```text
evaluation_sets/unseen_incoming_5_v1/
```

Frozen strata:

- corrected;
- revised;
- supersedure;
- long document;
- simple original.

They remain outside all E5 development/final benchmark construction.

Evaluate without retraining in two stages:

1. temporary-upload/unseen-document QA without permanent insertion;
2. permanent ingestion with duplicate rejection, deterministic extraction, lifecycle safeguards, index updates, and citations.

Unseen results must be reported separately from the 40-question final benchmark.

## Locking rules

- Do not retune parser v2.1.6 from locked extraction-test outcomes.
- Do not retune E0/E4 from QA-v2 outcomes.
- Tune E5 only on the 60-question E5 development set.
- Do not change frozen E5-D retrieval from final-test outcomes.
- Do not change the frozen hosted-QA configuration from final-test outcomes.
- Do not change final questions after the primary run.
- Do not replace the strict 38/40 primary score with oracle/post-hoc metrics.
- Do not use the five unseen PDFs to tune the frozen system.
- Preserve technical failures and exact-retry audit trails rather than silently rewriting first-pass results.
- Report failures, abstentions, ambiguities, stability issues, and negative results transparently.