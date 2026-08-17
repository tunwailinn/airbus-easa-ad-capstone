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
- Human semantic E5 final result: **38/40 = 95.0%**.
- Final oracle/reference-evidence diagnostic: **complete**.
- Five-PDF unseen source preparation: **complete**.
- Fifteen-question unseen QA set: **15/15 human reviewed and locked**.
- Unseen temporary-document primary run: **complete and preserved**.
- Unseen temporary human semantic review: **complete, human approved and locked**.
- U5Q-011 supplementary post-hoc identical retry: **failed with the same empty-final-content provider error; diagnostic only**.
- Next gate: **U5/U6 isolated permanent-ingestion evaluation**.

All extraction, retrieval, hosted-QA and E5 primary-final settings/results remain frozen. Unseen outcomes are post-final generalization results and must not be used for retuning.

## Layer A — deterministic extraction — PASS / FROZEN

Development primary (28 records):

- requested/successful corpus run: **1,804 / 1,804**;
- schema-valid: **100%**;
- stable metadata macro F1: **0.9948**;
- applicability-model F1: **0.9929**;
- reference-number F1: **0.8065**;
- superseded-AD-number F1: **1.0000**;
- difficult raw-section presence F1: **1.0000** for all five sections;
- source containment: **130/130**;
- contamination: **0**.

Clean locked extraction test primary (17 records):

- coverage/schema validity: **1.0000 / 1.0000**;
- stable metadata macro F1: **0.9831**;
- applicability-model F1: **0.9222**;
- reference-number F1: **0.9000**;
- superseded-AD-number F1: **0.6667**;
- difficult raw-section presence F1: **1.0000** for all five sections;
- source containment: **74/74**;
- contamination: **0**.

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

## E5 final benchmark — COMPLETE / IMMUTABLE

Primary automatic/retrieval result:

- hosted requests: **40/40 successful**;
- answerability/status accuracy: **1.0000**;
- Recall@5: **35/36 = 97.22%**;
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

- original oracle batch: **39 successes / 1 technical provider failure**;
- `E5F-021` becomes correct with oracle evidence → Layer B retrieval failure confirmed;
- `E5F-011` becomes correct with focused oracle evidence → Layer C evidence-selection/completeness sensitivity;
- `E5F-040` shows status-calibration/run-to-run variability;
- `E5F-035` exact transport retry recovered successfully.

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
- schema-valid: **5/5**.

### U2 unseen QA authoring/review — COMPLETE / LOCKED

- questions: **15**;
- exactly 3 per PDF;
- human verified: **15/15**;
- answerable: **14**;
- abstention: **1**;
- locked question SHA-256: `603d3385f5d083aeabf071d8d0c9be88896d31eb3f6530e881efeb3c03baeb2d`.

### U3 temporary-document QA — COMPLETE / PRESERVED

First-pass automatic result:

- hosted successes: **14/15 = 93.33%**;
- hosted failures: **1/15** (`U5Q-011`);
- answerability/status accuracy on successful requests: **13/14 = 92.86%**;
- reference-page any-overlap Recall@5: **14/14 = 100%**;
- reference-page full coverage@5: **14/14 = 100%**;
- reference-page citation hit: **100%**;
- target-AD citation hit: **100%**.

Post-hoc exact reference-quote containment diagnostic:

- any approved quote contained at top 5: **12/14 = 85.71%**;
- all approved quotes contained at top 5: **8/14 = 57.14%**.

These are diagnostic values only and do not replace the frozen page-level retrieval metrics.

### U4 temporary human semantic review — COMPLETE / HUMAN-APPROVED / LOCKED

Final result:

- semantic PASS: **13**;
- semantic FAIL: **1**;
- persistent provider/transport failure: **1**;
- semantic accuracy among successful first-pass responses: **13/14 = 92.86%**;
- strict first-pass end-to-end success: **13/15 = 86.67%**.

Human-approved interpretation:

- `U5Q-001`: **PASS**. The question did not ask for correction/supersedure dates; the hosted answer supplied all requested elements.
- `U5Q-010`: **FAIL — Layer B temporary passage selection**. Neither approved answer-bearing quote was present in top-5 prompt evidence.
- `U5Q-011`: **persistent provider/transport failure**. Primary request and the one permitted exact retry both returned empty final content; no semantic result is assigned.
- remaining 12 questions: **PASS**.

Locked result:

```text
evaluation_sets/unseen_incoming_5_v1/unseen_temporary_result_lock.json
```

Validator:

```text
full_corpus_pipeline/layer_c/validate_unseen_temporary_result_lock.py
```

### U5Q-011 supplementary post-hoc provider probe — FAILED / DIAGNOSTIC ONLY

A later extra request was run after the U3/U4 result was already locked. It reused the exact preserved prompt payload and frozen Layer C configuration without rerunning retrieval.

The post-hoc request also returned:

```text
DeepSeek JSON Output returned empty final content
```

Thus the same failure was observed on the primary request, the predeclared exact retry, and the later post-hoc identical request. This strengthens the classification as a persistent provider/structured-output failure for this payload. It does **not** change the locked unseen score.

Audit record:

```text
evaluation_sets/unseen_incoming_5_v1/u5q011_posthoc_extra_retry_observation.json
```

### U5/U6 permanent ingestion — NEXT / ALLOWED

Permanent ingestion may now proceed **only in an isolated evaluation store/index** after the temporary-result validator passes.

Required checks:

- exact SHA-256 duplicate rejection;
- frozen deterministic extraction;
- no model retraining;
- lifecycle/revision/correction/supersedure behavior;
- source provenance preservation;
- isolated index update behavior;
- repeat-ingestion rejection;
- post-ingestion QA and citations.

Frozen E5 indexes remain immutable.

## Reporting boundaries

Do not claim that:

- all 1,809 PDFs are strict Airbus S.A.S.-holder operational records;
- structured extraction fully normalizes complex compliance logic;
- the system makes aircraft-specific legal compliance determinations;
- oracle results replace the strict E5 final score;
- unseen results are part of the frozen 40-question E5 final score.

Original PDF passages remain authoritative for detailed applicability/compliance interpretation and page-cited QA.
