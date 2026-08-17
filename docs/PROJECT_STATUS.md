# Project Status

Last updated: 17 August 2026

## Current position

- Frozen physical snapshot: **1,809 PDFs / 1,808 base AD families**.
- Nominal development extraction: **1,804 PDFs**.
- Strict Airbus-only operational retrieval view: **1,786 PDFs / 6,002 verified pages**.
- Frozen parser: `content-local-v2.1.6`.
- Verified page source: `page-text-v1.1`.
- Frozen retrieval configuration: **E5-D**.
- Frozen hosted QA: **DeepSeek V4 Pro**.
- One-time 40-question E5 final benchmark: **complete**.
- Human semantic final result: **38/40 = 95.0%**.
- Final oracle/reference-evidence diagnostic: **complete**.
- Five-PDF unseen source preparation: **complete**.
- Fifteen-question unseen QA set: **15/15 human reviewed and locked**.
- Current next gate: **U3 temporary-document retrieval + frozen Layer C QA**.
- Permanent ingestion of the five held-out PDFs: **not started / prohibited until temporary QA review is preserved**.

All extraction, retrieval, hosted-QA and E5 primary-final settings/results remain frozen. Unseen outcomes are post-final generalization results and must not be used for retuning.

## Layer A — deterministic extraction — PASS / FROZEN

Development primary (28 records):

- requested/successful corpus run: **1,804 / 1,804**;
- schema-valid: **100%**;
- stable metadata macro F1: **0.9948**;
- applicability-model F1: **0.9929**;
- reference-number F1: **0.8065**;
- superseded-AD-number F1: **1.0000**;
- all five difficult raw-section presence F1 values: **1.0000**;
- source containment: **130/130**;
- contamination: **0**.

Clean locked extraction test primary (17 records):

- coverage/schema validity: **1.0000 / 1.0000**;
- stable metadata macro F1: **0.9831**;
- applicability-model F1: **0.9222**;
- reference-number F1: **0.9000**;
- superseded-AD-number F1: **0.6667**;
- all five difficult raw-section presence F1 values: **1.0000**;
- source containment: **74/74**;
- contamination: **0**.

## Corpus scope

- strict Airbus-only operational records: **1,786**;
- retained external/mixed-holder records: **18**;
- unresolved unknowns: **0**.

Scope filtering never deletes physical/source records.

## Layer B source layer — PASS / FROZEN

Verified original-PDF page source:

```text
data_processed/page_text_v1_1/operational_airbus/
```

- selected/successful: **1,786 / 1,786**;
- pages: **6,002**;
- failures: **0**;
- unresolved weak/OCR pages: **0**;
- one reviewed visual override: AD `2011-0006`, page 3.

## Historical E0/E4 retrieval — CLOSED

Frozen build:

```text
data_processed/indexes/rag_v1_2/
```

- E0: 9,394 flat dense chunks; QA-v2 Recall@5 **0.0000**.
- E4: 12,634 section-aware chunks; QA-v2 Recall@5 **0.4091**.

E4's observed gain was primarily lexical/section-aware. These are historical results and are not tuning targets.

## E5-D engineering-aware retrieval — FROZEN

Development result:

- Recall@1: **0.7963**;
- Recall@3: **0.9259**;
- Recall@5: **0.9630**;
- MRR@5: **0.8633**;
- nDCG@5: **0.8884**;
- correct source+page@5: **0.9630**;
- candidate source+page recall@20: **0.9815**;
- known-document Recall@5: **1.0000 (36/36)**;
- discovery Recall@5: **0.8889 (16/18)**.

Frozen stack:

- E5-C BM25 + `Qwen/Qwen3-Embedding-0.6B@97b0c61` candidate generation;
- candidate depth 20;
- `Qwen/Qwen3-Reranker-0.6B@e61197e` reranker;
- final evidence depth 5;
- deterministic known-document routing.

Retrieval freeze:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/retrieval_freeze.json
```

## Layer C hosted QA — FROZEN

```text
provider: DeepSeek official API
adapter: deepseek-direct-v1.1
model: deepseek-v4-pro
thinking: enabled
reasoning_effort: high
max_tokens: 4096
prompt: e5-hosted-qa-prompt-v1.0-dev
response contract: e5-hosted-qa-contract-v1.0
semantic retry: prohibited
```

Hosted-QA freeze:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/hosted_qa_freeze.json
```

## E5 final benchmark — COMPLETE / IMMUTABLE

Final set:

- **40 human-reviewed questions**;
- 36 answerable + 4 abstention/conflict;
- 24 known-document + 12 identifier-free discovery + 4 abstention/conflict.

Automatic primary result:

- hosted requests: **40/40 successful**;
- answerability/status accuracy: **1.0000**;
- Recall@1/3/5: **0.8333 / 0.9722 / 0.9722**;
- Recall@5: **35/36 = 97.22%**;
- MRR@5: **0.8981**;
- nDCG@5: **0.9173**;
- known-document Recall@5: **24/24 = 100%**;
- discovery Recall@5: **11/12 = 91.67%**.

Human semantic primary result:

- semantic passes: **38/40**;
- semantic failures: **2/40**;
- strict end-to-end semantic accuracy: **95.0%**.

Primary failures:

- `E5F-011`: Layer C answer-selection/completeness failure under retrieved evidence;
- `E5F-021`: Layer B retrieval/candidate-generation failure.

The 95.0% primary result is authoritative and cannot be replaced by oracle/post-hoc values.

## Final oracle diagnostic — COMPLETE

Original oracle batch: **39 successes / 1 technical provider failure**.

Key findings:

- `E5F-021` becomes correct with oracle evidence → Layer B retrieval failure confirmed;
- `E5F-011` becomes correct with focused oracle evidence → Layer C evidence-selection/completeness sensitivity;
- `E5F-040` shows status-calibration/run-to-run variability under unchanged negative-control evidence;
- `E5F-035` exact transport retry recovered successfully without changing prompt/evidence/config.

Oracle results remain diagnostic only.

## Five-PDF unseen-document generalization — ACTIVE

Frozen set:

| Stratum | AD | Pages |
|---|---|---:|
| corrected | 2008-0008 | 2 |
| revised | 2011-0041R1 | 4 |
| supersedure | 2011-0142 | 3 |
| long document | 2026-0084 | 10 |
| simple original | 2007-0173 | 2 |

### U0/U1 preparation — COMPLETE

- source SHA matches: **5/5**;
- total pages: **21**;
- deterministic extraction success: **5/5**;
- schema-valid: **5/5**;
- no hosted inference performed;
- no permanent ingestion performed.

### U2 unseen QA authoring/review — COMPLETE / LOCKED

- questions: **15**;
- exactly 3 per PDF;
- human verified: **15/15**;
- answerable: **14**;
- abstention: **1**;
- locked question SHA-256: `603d3385f5d083aeabf071d8d0c9be88896d31eb3f6530e881efeb3c03baeb2d`.

Lock/audit:

```text
evaluation_sets/unseen_incoming_5_v1/unseen_lock.json
evaluation_sets/unseen_incoming_5_v1/unseen_question_verification_audit.json
evaluation_sets/unseen_incoming_5_v1/unseen_question_final_review.md
```

U5Q-008's reviewer-requested wording check was verified against the `2011-0142` source packet and retained unchanged.

### U3 temporary QA — NEXT

```text
validate unseen question lock
→ rerank only the selected temporary PDF's prepared chunks
→ top-5 evidence
→ frozen Layer C DeepSeek QA
→ preserve first-pass result
→ offline automatic + human semantic review
```

Implementation:

```text
full_corpus_pipeline/layer_c/validate_unseen_question_lock.py
full_corpus_pipeline/layer_c/run_unseen_temporary_qa.py
full_corpus_pipeline/layer_c/evaluate_unseen_temporary_qa.py
```

### U5 permanent ingestion — BLOCKED

Do not permanently ingest any of the five PDFs until U3/U4 temporary results are preserved and reviewed. Permanent ingestion will then be tested separately in an isolated evaluation store/index for duplicate rejection, lifecycle behavior, index update, repeat-ingestion rejection, and post-ingestion citations.

## Reporting boundaries

Do not claim that:

- all 1,809 PDFs are strict Airbus S.A.S.-holder operational records;
- structured extraction fully normalizes complex compliance logic;
- the system makes aircraft-specific legal compliance determinations;
- oracle results replace the strict E5 final score;
- unseen results are part of the frozen 40-question E5 final score.

Original PDF passages remain authoritative for detailed applicability/compliance interpretation and page-cited QA.
