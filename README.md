# Airbus EASA AD Extraction and RAG Capstone

Intelligent engineering document automation for Airbus S.A.S. Airworthiness Directives issued by EASA.

The project processes a frozen snapshot of **1,809 Airbus-related EASA AD PDFs / 1,808 base AD families** and evaluates a three-layer architecture:

```text
Layer A — deterministic structured extraction
→ metadata, lifecycle fields, exact source-derived raw sections

Layer B — verified original-PDF retrieval
→ page-preserving evidence, engineering-aware retrieval, lifecycle-aware routing

Layer C — hosted evidence-grounded QA
→ answer | insufficient_evidence | conflicting_evidence
→ source/page/section citations resolved from evidence metadata
```

Five PDFs are held out from all development/final benchmark work for the last unseen-document ingestion/generalization evaluation.

Complex compliance semantics are intentionally interpreted from original-PDF evidence at question time. Full-corpus extraction and indexing do **not** use a hosted LLM; DeepSeek V4 Pro is used only in the frozen Layer C QA condition.

## Current status — 14 August 2026

Completed and frozen:

- Layer A extraction development + clean locked test;
- strict Airbus S.A.S. scope audit;
- verified original-PDF page-text layer;
- E0/E4 historical retrieval experiments;
- E5-A/B/C/D engineering-aware retrieval development;
- E5-D retrieval freeze;
- Layer C DeepSeek V4 Pro development and hosted-QA freeze;
- human-reviewed 40-question final benchmark lock;
- one-time final benchmark;
- human semantic final review;
- final oracle/reference-evidence diagnostic;
- exact audited transport retry for one oracle provider failure.

**Authoritative primary final semantic accuracy: 38/40 = 95.0%.**

Remaining major evaluation:

- five frozen unseen-PDF temporary-QA + permanent-ingestion cases.

## Corpus and frozen extraction

- physical snapshot: **1,809 PDFs**;
- base AD families: **1,808**;
- nominal development extraction: **1,804 PDFs**;
- strict Airbus-only operational view: **1,786 PDFs**;
- verified operational pages: **6,002**;
- external/mixed-holder records retained outside strict operational view: **18**;
- unresolved holder-scope unknowns: **0**.

Frozen extraction stack:

- content schema: `2.1.0`;
- parser: **`content-local-v2.1.6`**;
- evaluator: **`content-eval-v3.1.5`**;
- scope audit: **`corpus-scope-audit-v1.3`**;
- immutable gold source: `gold_releases/easa_airbus_ad_gold_v2/`.

### Development extraction result

Primary development count: 28.

- prediction coverage: **1.0000**;
- schema validity: **1.0000**;
- stable metadata macro F1: **0.9948**;
- applicability-model F1: **0.9929**;
- reference-number F1: **0.8065**;
- superseded-AD-number F1: **1.0000**;
- all five difficult raw-section presence F1 values: **1.0000**;
- source containment: **130/130**;
- detected contamination: **0**.

### Clean locked extraction test

Primary clean count: 17 after holder-scope exclusions plus the disclosed `2024-0038` leakage exclusion.

- coverage/schema validity: **1.0000 / 1.0000**;
- stable metadata macro F1: **0.9831**;
- applicability-model F1: **0.9222**;
- reference-number F1: **0.9000**;
- superseded-AD-number F1: **0.6667**;
- all five difficult raw-section presence F1 values: **1.0000**;
- source containment: **74/74**;
- detected contamination: **0**.

Parser v2.1.6 is frozen. These test outcomes are reported, not used for retuning.

## Verified source layer

Canonical original-PDF page source:

```text
data_processed/page_text_v1_1/operational_airbus/
```

- documents: **1,786 / 1,786 successful**;
- pages: **6,002**;
- failures: **0**;
- unresolved weak/OCR pages: **0**;
- one reviewed visual override: AD `2011-0006`, page 3;
- `ready_for_indexing=true`.

## Retrieval

Historical E0/E4 build:

```text
data_processed/indexes/rag_v1_2/
```

- E0: **9,394** flat dense chunks;
- E4: **12,634** section-aware chunks, including **2,924** multi-page chunks.

QA-v2 historical Recall@5:

- E0: **0.0000**;
- E4: **0.4091**.

These experiments motivated the later E5 engineering-aware retrieval design and remain frozen historical results.

## E5-D — selected engineering-aware retrieval

E5 benchmark:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/
```

Development:

- 24 development families;
- 60 human-reviewed development questions;
- 36 known-document + 18 identifier-free discovery + 6 abstention/conflict.

Selected E5-D stack:

- deterministic known-document routing;
- E5-C BM25 + `Qwen/Qwen3-Embedding-0.6B@97b0c61` candidate generation;
- fixed candidate depth: **20**;
- `Qwen/Qwen3-Reranker-0.6B@e61197e` reranking;
- final evidence depth: **5**;
- frozen E4 section chunks.

Development result:

- Recall@1: **0.7963**;
- Recall@3: **0.9259**;
- Recall@5: **0.9630**;
- MRR@5: **0.8633**;
- nDCG@5: **0.8884**;
- correct source+page@5: **0.9630**;
- candidate source+page recall@20: **0.9815**;
- known-document Recall@5: **1.0000**;
- discovery Recall@5: **0.8889**.

Retrieval is frozen in:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/retrieval_freeze.json
```

## Layer C — frozen hosted QA

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

Hosted-QA freeze:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/hosted_qa_freeze.json
```

The model receives only the question and evidence. Private reference answers, target labels, reference pages, query-mode/category labels, and answerability labels are withheld during generation.

## One-time E5 final benchmark

Final set:

- 16 final-test families;
- **40 human-reviewed questions**;
- 36 answerable + 4 abstention/conflict;
- 24 known-document + 12 identifier-free discovery + 4 abstention/conflict;
- final questions SHA-256: `f6b008c1b5d24160cb5718e2d4e91a7e0d323277a531654e4b5c3a33995c9a85`.

### Primary automatic result

- hosted requests: **40/40 = 100% successful**;
- answerability/status accuracy: **100%**;
- retrieval Recall@5: **35/36 = 97.22%**;
- MRR@5: **0.8981**;
- nDCG@5: **0.9173**;
- known-document Recall@5: **24/24 = 100%**;
- discovery Recall@5: **11/12 = 91.67%**;
- reference-page citation hit rate: **97.22%**;
- target-AD citation hit rate: **97.22%**.

### Human semantic final result

- passes: **38/40**;
- failures: **2/40**;
- **strict end-to-end semantic accuracy: 95.0%**.

This 95.0% result is authoritative and may not be replaced by post-hoc or oracle-adjusted scores.

Primary failures:

- `E5F-011` — Layer C answer-selection/completeness failure under retrieved evidence;
- `E5F-021` — Layer B retrieval/candidate-generation failure.

## Final oracle/reference-evidence diagnostic

Oracle/reference evidence changes only the evidence condition; provider/model/prompt/settings remain identical.

Original oracle batch:

- 40 selected;
- 39 successful;
- one technical/provider failure (`E5F-035`);
- reference-page citation hit rate: **100%**;
- target-AD citation hit rate: **100%**.

Findings:

- `E5F-021` becomes correct → **Layer B retrieval failure confirmed**;
- `E5F-011` becomes correct with focused evidence → **Layer C evidence-selection/completeness sensitivity**;
- `E5F-040` changed machine-readable status despite unchanged negative-control evidence → **Layer C status-calibration/run-to-run variability**;
- `E5F-035` original empty-JSON provider failure was recovered by one exact audited transport retry with unchanged prompt/evidence/config.

The oracle condition is diagnostic only; the primary final score remains **38/40 = 95.0%**.

Detailed final evaluation:

```text
docs/LAYER_C_FINAL_EVALUATION.md
```

## Next stage — five frozen unseen PDFs

The remaining major evaluation is:

```text
evaluation_sets/unseen_incoming_5_v1/
```

Five distinct held-out strata:

- corrected;
- revised;
- supersedure;
- long document;
- simple original.

Evaluate without retraining:

1. temporary unseen-document QA without permanent insertion;
2. permanent ingestion with duplicate rejection, deterministic extraction, lifecycle decision, index update, and page-cited QA.

Do not use unseen outcomes to retune the frozen primary system.

## Reporting boundaries

- The 1,809 physical PDFs are Airbus-related, not all strict Airbus S.A.S.-holder operational records.
- The 18 external/mixed-holder records remain preserved for provenance.
- Structured extraction does not fully normalize all complex compliance logic.
- Original PDF passages remain authoritative for detailed applicability/compliance interpretation.
- The system does not make aircraft-specific legal compliance determinations.
- Oracle and exact-retry results are diagnostic and cannot replace the strict primary final result.