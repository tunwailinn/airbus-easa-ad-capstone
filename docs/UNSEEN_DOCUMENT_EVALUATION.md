# Frozen Five-PDF Unseen-Document Evaluation

## Status — COMPLETE / LOCKED

This is the post-final generalization experiment performed after the frozen E5-D retrieval configuration, frozen hosted-QA configuration, one-time 40-question final benchmark, human semantic review, and final oracle diagnostic.

The authoritative E5 primary result remains unchanged:

- 40 final questions;
- 38 semantic passes / 2 semantic failures;
- strict end-to-end semantic accuracy: **95.0%**;
- E5-D final Recall@5: **35/36 = 97.22%**.

The unseen experiment is complete through **U8**. Its results are separate from the frozen 40-question E5 final benchmark and may not be used to retrospectively retune the parser, retrieval stack, prompt, DeepSeek settings, response contract, or evidence depth.

## Frozen unseen set

| Stratum | AD | Pages |
|---|---|---:|
| corrected | 2008-0008 | 2 |
| revised | 2011-0041R1 | 4 |
| supersedure | 2011-0142 | 3 |
| long document | 2026-0084 | 10 |
| simple original | 2007-0173 | 2 |

Total: **5 PDFs / 21 pages**.

## U0/U1 — source validation and non-destructive preparation — COMPLETE

- source SHA matches: **5/5**;
- deterministic extraction success: **5/5**;
- schema valid: **5/5**;
- parser: `content-local-v2.1.6`;
- permanent ingestion during preparation: **false**.

Preparation manifest SHA-256:

```text
e3a60433348003b8e238a6704d40ddcd6e389e4f7804df92057f4eec9bbadc05
```

## U2 — human-reviewed unseen question lock — COMPLETE / LOCKED

- questions: **15**;
- exactly three per PDF;
- answerable: **14**;
- abstention: **1**;
- human verified: **15/15**.

Locked question SHA-256:

```text
603d3385f5d083aeabf071d8d0c9be88896d31eb3f6530e881efeb3c03baeb2d
```

## U3/U4 — temporary-document condition — COMPLETE / HUMAN-APPROVED / LOCKED

First-pass hosted result:

- hosted successes: **14/15 = 93.33%**;
- hosted failure: **U5Q-011**;
- page-overlap Recall@5 on answerable questions: **14/14 = 100%**.

Human-approved semantic result:

- PASS: **13**;
- semantic FAIL: **1** (`U5Q-010`);
- technical/provider failure: **1** (`U5Q-011`);
- semantic accuracy among successful responses: **13/14 = 92.86%**;
- strict first-pass end-to-end success: **13/15 = 86.67%**.

Attribution:

- `U5Q-010`: **Layer B temporary passage-selection failure**. Page 1 overlapped top-5, but neither approved answer-bearing `Supersedure` nor `Applicability` quote was actually supplied to Layer C.
- `U5Q-011`: persistent DeepSeek empty-final-content provider/structured-output failure. The primary request, one exact temporary retry, and a later diagnostic identical probe all failed. These supplementary attempts do not rewrite U3/U4.

Locked result:

```text
evaluation_sets/unseen_incoming_5_v1/unseen_temporary_result_lock.json
```

## U5/U6 — isolated permanent ingestion and safeguards — COMPLETE / PASS

The five held-out PDFs were admitted only to an isolated evaluation store/index after the U3/U4 lock validated.

Technical safeguards:

- ingestion success: **5/5**;
- AD identity match: **5/5**;
- frozen parser match: **5/5**;
- deterministic record match against U1: **5/5**;
- copied source SHA match: **5/5**;
- isolated E4 append checks: **5/5**;
- isolated E5-C row-alignment checks: **5/5**;
- exact duplicate rejection with no mutation: **5/5**;
- lifecycle decisions recorded: **5/5**;
- frozen E4 unchanged: **true**;
- frozen E5-C unchanged: **true**;
- normal `data_incoming/` unchanged: **true**.

The isolated derivative grew:

```text
documents: 1,786 → 1,791
chunks:    12,634 → 12,670
```

The U5/U6 result is a technical-safeguard pass, not a claim that every structured Layer A field is semantically perfect. Some unseen `revision_statement` captures are over-broad but exactly reproduce the pre-ingestion U1 records, so they are pre-existing extraction limitations rather than ingestion regressions.

Committed lock:

```text
evaluation_sets/unseen_incoming_5_v1/unseen_permanent_ingestion_result_lock.json
```

## Pre-U7 frozen-chunk-policy compatibility gate — COMPLETE / PASS

The five appended documents were reconstructed with the frozen E4 strict section-chunk policy.

- selected documents: **5**;
- exact match: **5/5**;
- chunk counts and chunk IDs matched exactly;
- `all_exact`: **true**.

This confirms U7 used the same chunking policy as the frozen E5 retrieval stack.

## U7 — post-ingestion E5-D + frozen Layer C — COMPLETE / HUMAN-APPROVED / LOCKED

Frozen algorithm/configuration retained:

- E5-C BM25 + `Qwen/Qwen3-Embedding-0.6B@97b0c61`;
- candidate depth: **20**;
- E5-D `Qwen/Qwen3-Reranker-0.6B@e61197e`;
- evidence depth: **5**;
- DeepSeek `deepseek-v4-pro`;
- thinking enabled, reasoning effort high, max tokens 4096;
- prompt `e5-hosted-qa-prompt-v1.0-dev`;
- no frozen E5 artifact mutation;
- no retrieval retuning.

### U7 retrieval — 14 answerable questions

- Recall@1: **13/14 = 92.86%**;
- Recall@3: **14/14 = 100%**;
- Recall@5: **14/14 = 100%**;
- MRR@5: **96.43%**;
- nDCG@5: **97.36%**;
- correct source@1: **14/14 = 100%**;
- correct source+page@5: **14/14 = 100%**;
- candidate source+page recall@20: **14/14 = 100%**.

### U7 human semantic result

- hosted successes: **14/15**;
- semantic PASS: **13**;
- semantic FAIL: **1** (`U5Q-010`);
- technical/provider failure: **1** (`U5Q-011`);
- semantic accuracy among successful responses: **13/14 = 92.86%**;
- strict primary end-to-end success: **13/15 = 86.67%**.

Human-approved review:

```text
evaluation_sets/unseen_incoming_5_v1/u7_post_ingestion_human_semantic_review_final.md
```

Human-review lock:

```text
evaluation_sets/unseen_incoming_5_v1/u7_post_ingestion_human_semantic_review_lock.json
```

### U5Q-010 — final attribution

Page-level E5-D reports a reference-page hit, but neither approved answer-bearing `Supersedure` nor `Applicability` quote is in the top-five prompt evidence. The hosted `insufficient_evidence` response is therefore attributed to **Layer B post-ingestion passage selection**, not Layer C reasoning.

This is the key retrieval lesson from the unseen experiment:

> Correct source/page Recall@5 does not necessarily guarantee that the answer-bearing passage is available to the generator.

### U5Q-011 — final attribution

Both approved reference quotations are present in the U7 top-five evidence. The primary request nevertheless returned:

```text
DeepSeek JSON Output returned empty final content
```

The single exact U7 transport retry reused the identical post-ingestion question/evidence/prompt payload and frozen Layer C configuration, without rerunning retrieval. It failed with the same error.

Therefore `U5Q-011` is a **provider/structured-output technical failure**, not a retrieval failure. No further retry is part of the evaluation protocol.

Post-ingestion prompt-payload SHA-256:

```text
7a85360c8bfcb9bf9dff5f2932d6381e75b3bb740a8b271192501143c634ba5b
```

### Passage-support diagnostic

Across 14 answerable U7 questions:

- any approved reference quote contained@5: **12/14 = 85.71%**;
- all approved reference quotes contained@5: **8/14 = 57.14%**.

These are diagnostics only. Exact-string containment can be false even when supplied evidence is semantically sufficient, as demonstrated by correct `U5Q-014` and `U5Q-015` responses.

## U8 — final unseen-generalization report — COMPLETE / LOCKED

Canonical report:

```text
docs/U8_FINAL_UNSEEN_GENERALIZATION_REPORT.md
```

Final completion lock:

```text
evaluation_sets/unseen_incoming_5_v1/unseen_final_generalization_lock.json
```

Validator:

```text
full_corpus_pipeline/layer_c/validate_unseen_final_generalization.py
```

Final comparison:

| Evaluation condition | Retrieval | Human semantic result | Strict end-to-end |
|---|---|---|---|
| Frozen 40-question E5 final | Recall@5 35/36 = 97.22% | 38/40 PASS = 95.0% | 95.0% |
| Unseen temporary U3/U4 | Page Recall@5 14/14 = 100% | 13 PASS / 1 FAIL / 1 technical | 13/15 = 86.67% |
| Unseen post-ingestion U7 | E5-D Recall@5 14/14 = 100% | 13 PASS / 1 FAIL / 1 technical | 13/15 = 86.67% |

The **95.0% frozen E5 primary result remains the project's authoritative final benchmark score**. The unseen results are separate post-final evidence of generalization, ingestion robustness, and remaining system limitations.

## Evaluation sequence

```text
U0 source/selection validation                         COMPLETE
U1 non-destructive preparation                         COMPLETE
U2 human-reviewed unseen QA authoring + lock           COMPLETE / LOCKED
U3 temporary-document retrieval + frozen Layer C QA    COMPLETE / PRESERVED
U4 temporary human semantic review                     COMPLETE / LOCKED
U5 isolated permanent ingestion                        COMPLETE / PASS
U6 duplicate/lifecycle/index-update safeguards         COMPLETE / PASS
U7 post-ingestion E5-D + Layer C + human review        COMPLETE / LOCKED
U8 final unseen-generalization report                  COMPLETE / LOCKED
```

## Interpretation boundary

Do not claim that:

- all 1,809 PDFs are strict Airbus S.A.S.-holder operational records;
- structured extraction fully normalizes complex compliance logic;
- correct source/page retrieval always implies answer-bearing passage retrieval;
- the system makes aircraft-specific legal compliance determinations;
- oracle/retry/unseen results replace the strict E5 final score;
- unseen results are part of the frozen 40-question E5 final benchmark.

Original PDF passages remain authoritative for detailed applicability/compliance interpretation and page-cited QA. Future engineering changes are post-evaluation work and must not rewrite the preserved results above.
