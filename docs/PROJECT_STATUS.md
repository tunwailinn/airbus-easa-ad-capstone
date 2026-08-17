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
- Unseen temporary-document primary run: **complete and preserved**.
- Unseen temporary human semantic review: **pending final reviewer approval**.
- Permanent ingestion of the five held-out PDFs: **not started / blocked until the temporary semantic result is locked**.

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

- E0: 9,394 flat dense chunks; QA-v2 Recall@5 **0.0000**.
- E4: 12,634 section-aware chunks; QA-v2 Recall@5 **0.4091**.

These are frozen historical experiments.

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

Primary retrieval/automatic result:

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
- schema-valid: **5/5**;
- no permanent ingestion performed.

### U2 unseen QA authoring/review — COMPLETE / LOCKED

- questions: **15**;
- exactly 3 per PDF;
- human verified: **15/15**;
- answerable: **14**;
- abstention: **1**;
- locked question SHA-256: `603d3385f5d083aeabf071d8d0c9be88896d31eb3f6530e881efeb3c03baeb2d`.

### U3 temporary-document QA — FIRST PASS COMPLETE

Frozen first-pass automatic result:

- hosted successes: **14/15 = 93.33%**;
- hosted failures: **1/15** (`U5Q-011`);
- answerability/status accuracy on successful requests: **13/14 = 92.86%**;
- reference-page any-overlap Recall@5: **14/14 = 100%**;
- reference-page full coverage@5: **14/14 = 100%**;
- reference-page citation hit: **100%**;
- target-AD citation hit: **100%**;
- permanent ingestion started: **false**.

A post-hoc exact reference-quote containment diagnostic found:

- any approved quote contained at top 5: **12/14 = 85.71%**;
- all approved quotes contained at top 5: **8/14 = 57.14%**.

These are diagnostic values only; they do not replace the frozen page-level retrieval metrics.

Confirmed attribution diagnostic:

- `U5Q-010`: page 1 was represented in top-5, but neither approved answer-bearing `Supersedure` nor `Applicability` quote was actually supplied → **temporary passage-selection failure**.

### U5Q-011 transport failure — CLOSED

Primary request: DeepSeek returned empty final JSON content.

One exact transport retry was performed with the identical prompt payload SHA-256:

```text
b17e0b69d1a7a28071cb9fc219272e4dc6e755223426cc39e08bd98ca66e5f33
```

The retry failed again with the same empty-final-content error. No further retry is permitted. This is recorded as a **persistent provider/transport failure**, not a semantic Layer C failure.

### U4 temporary human semantic review — PENDING APPROVAL

AI-assisted provisional assessment:

- `U5Q-001`: proposed **FAIL — Layer C completeness**;
- `U5Q-010`: proposed **FAIL — Layer B temporary passage selection**;
- `U5Q-011`: **persistent technical/provider failure**;
- remaining 12 questions: proposed **PASS**.

If explicitly approved by the human reviewer, the unseen temporary-QA result will be reported as:

- semantic accuracy among successful first-pass responses: **12/14 = 85.71%**;
- strict first-pass end-to-end success: **12/15 = 80.0%**;
- semantic failures: **2**;
- persistent provider/transport failures: **1**.

These values are not human-finalized yet.

### U5 permanent ingestion — BLOCKED

Do not permanently ingest any of the five PDFs until U4 temporary semantic decisions are explicitly approved and preserved. Permanent ingestion will then be tested separately in an isolated evaluation store/index for duplicate rejection, lifecycle behavior, index update, repeat-ingestion rejection, and post-ingestion citations.

## Reporting boundaries

Do not claim that:

- all 1,809 PDFs are strict Airbus S.A.S.-holder operational records;
- structured extraction fully normalizes complex compliance logic;
- the system makes aircraft-specific legal compliance determinations;
- oracle results replace the strict E5 final score;
- unseen results are part of the frozen 40-question E5 final score;
- the provisional unseen semantic score is human-reviewed before explicit reviewer approval.

Original PDF passages remain authoritative for detailed applicability/compliance interpretation and page-cited QA.
