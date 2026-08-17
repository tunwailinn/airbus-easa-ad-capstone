# Frozen Five-PDF Unseen-Document Evaluation

## Status

This is the post-final generalization experiment performed after the frozen E5-D retrieval configuration, frozen hosted-QA configuration, one-time 40-question final benchmark, human semantic review, and final oracle diagnostic.

The E5 primary result remains authoritative and unchanged:

- 40 final questions;
- 38 semantic passes / 2 semantic failures;
- strict end-to-end semantic accuracy: **95.0%**;
- E5-D final Recall@5: **35/36 = 97.22%**.

Unseen outcomes are reported separately and may not be used to retune the frozen parser, retrieval stack, prompt, DeepSeek model/settings, response contract, or evidence depth.

## Current checkpoint — 17 August 2026

### U0/U1 — source validation + non-destructive preparation — COMPLETE

Verified preparation result:

- preparation version: `unseen-5-preparation-v1.0`;
- frozen documents: **5/5**;
- exact source SHA-256 matches: **5/5**;
- source pages: **21**;
- deterministic extraction successes: **5/5**;
- schema-valid extracted records: **5/5**;
- parser: `content-local-v2.1.6`;
- hosted inference started during preparation: **false**;
- permanent ingestion started during preparation: **false**.

Preparation bindings:

```text
selection.csv SHA-256:
f175477d68e2226b0793d742ad1ef0de99053b57e8334f1ca2c2962723e8c6a5

selection_lock.json SHA-256:
d2d12b393d544aff8f1c69dcff89a5305011b504f8ee54281dd40e20d725fd2c

corpus_manifest.parquet SHA-256:
00e7995de1ebfae1ebbc64fc447d7953567a3ef59854620bce0b606ac4f40a18

preparation_manifest.json SHA-256:
e3a60433348003b8e238a6704d40ddcd6e389e4f7804df92057f4eec9bbadc05
```

### U2 — human-reviewed unseen QA authoring + lock — COMPLETE

The unseen QA set contains **15 questions, exactly three per held-out PDF**.

Human-review outcome:

- reviewed: **15/15**;
- human verified: **15/15**;
- rejected: **0**;
- revised question/reference records: **0**;
- answerable from AD: **14**;
- abstention/insufficient-evidence: **1**.

Locked category composition:

| Category | Count |
|---|---:|
| identity/lifecycle | 4 |
| applicability | 3 |
| required action/compliance | 3 |
| conditional/multi-passage | 3 |
| referenced publication | 1 |
| insufficient/conflict/abstention | 1 |
| **Total** | **15** |

Locked question SHA-256:

```text
603d3385f5d083aeabf071d8d0c9be88896d31eb3f6530e881efeb3c03baeb2d
```

Committed lock/audit records:

```text
evaluation_sets/unseen_incoming_5_v1/unseen_lock.json
evaluation_sets/unseen_incoming_5_v1/unseen_question_verification_audit.json
evaluation_sets/unseen_incoming_5_v1/unseen_question_final_review.md
```

`unseen_questions.jsonl` is installed locally and is bound by the committed SHA-256 lock, matching the sealed-local-file pattern used for the final E5 question set.

### U5Q-008 verification note

The reviewer approved U5Q-008 but requested verification of the statement that Airbus issued a new AFM procedure applicable to all aeroplanes. The prepared `2011-0142` source packet states:

> Airbus has issued a new AFM procedure, applicable to all aeroplanes.

The question/reference record is therefore retained unchanged.

## Frozen unseen set

| Stratum | AD | Pages |
|---|---|---:|
| corrected | 2008-0008 | 2 |
| revised | 2011-0041R1 | 4 |
| supersedure | 2011-0142 | 3 |
| long_document | 2026-0084 | 10 |
| simple_original | 2007-0173 | 2 |

These five families were excluded from development extraction, verified page-text indexing, E0/E4, E5 development, E5 final benchmark construction, and hosted-QA selection.

## Evaluation sequence

```text
U0 source/selection validation                         COMPLETE
→ U1 non-destructive unseen preparation               COMPLETE
→ U2 human-reviewed unseen QA authoring + lock         COMPLETE
→ U3 temporary-document retrieval + frozen Layer C QA  NEXT
→ U4 offline/human temporary-QA evaluation             NOT STARTED
→ U5 permanent ingestion into isolated evaluation      PROHIBITED UNTIL U4 PRESERVED
→ U6 duplicate/lifecycle/index-update safeguards       NOT STARTED
→ U7 post-ingestion QA/citation verification           NOT STARTED
→ U8 final unseen-generalization report                NOT STARTED
```

Do not permanently ingest a held-out PDF before the temporary-document primary result and human semantic review have been preserved.

## U3 — locked temporary-document QA

Validator:

```text
full_corpus_pipeline/layer_c/validate_unseen_question_lock.py
```

Primary runner:

```text
full_corpus_pipeline/layer_c/run_unseen_temporary_qa.py
```

Offline evaluator:

```text
full_corpus_pipeline/layer_c/evaluate_unseen_temporary_qa.py
```

Temporary retrieval is intentionally document-scoped. Each question uses only the prepared section chunks from its selected held-out PDF. Every held-out PDF has at most 14 prepared chunks, so all chunks are passed to the pinned E5-D Qwen reranker; only the top five are supplied to Layer C.

Frozen answer-generation configuration remains:

```text
provider: DeepSeek official API
model: deepseek-v4-pro
thinking: enabled
reasoning_effort: high
max_tokens: 4096
prompt: e5-hosted-qa-prompt-v1.0-dev
response contract: e5-hosted-qa-contract-v1.0
semantic retry: prohibited
```

The temporary runner does not write to `data_incoming/`, does not alter a persistent retrieval index, does not change lifecycle state, and does not perform permanent ingestion.

Primary temporary-QA metrics:

- source/preparation success;
- temporary retrieval any-reference-page Recall@5;
- temporary retrieval full-reference-page coverage@5;
- hosted request success;
- answerability/status accuracy;
- reference-page citation hit rate;
- target-AD citation hit rate;
- human semantic answer accuracy;
- condition/timing/exception completeness;
- unsupported-claim rate;
- abstention correctness.

## U5/U6 — permanent ingestion — NOT STARTED

Permanent ingestion starts only after U3/U4 results are preserved. It must use an isolated unseen-evaluation store/index first and test:

- exact SHA-256 duplicate rejection;
- frozen deterministic extraction;
- no model retraining;
- lifecycle/revision/correction/supersedure decisions;
- source provenance preservation;
- index append behavior;
- repeat-ingestion rejection;
- post-ingestion QA and citations.

Frozen E5 benchmark indexes remain immutable audit artifacts.

## Interpretation boundary

Unseen failures must be attributed to the stage that caused them: source preparation, deterministic extraction, temporary passage selection, Layer C generation/status, duplicate handling, lifecycle handling, index update, or post-ingestion retrieval/QA.

Do not silently fix a held-out failure and report the fixed output as the original unseen result. Any later fix is post-hoc engineering work and must be labelled separately.
