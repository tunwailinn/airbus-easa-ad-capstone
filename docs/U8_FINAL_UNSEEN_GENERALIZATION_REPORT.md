# U8 Final Unseen-Document Generalization Report

**Date:** 2026-08-18  
**Scope:** Five frozen unseen Airbus S.A.S. EASA AD PDFs  
**Status:** Complete

## Executive result

The unseen evaluation tested whether the frozen extraction, retrieval and hosted-QA architecture
generalizes to five held-out documents covering correction, revision, supersedure, long-document
and simple-original cases.

The five-document ingestion pipeline passed all technical safeguards. After isolated permanent
ingestion, frozen E5-D retrieval achieved **100% Recall@5 (14/14)** and **100% correct-source@1
(14/14)** on the answerable unseen questions. Human semantic review of the hosted-QA primary
result produced **13 PASS, 1 semantic FAIL and 1 technical provider failure**.

The final U7 primary unseen rates are:

- semantic accuracy among successful hosted responses: **13/14 = 92.86%**;
- strict primary end-to-end success: **13/15 = 86.67%**.

These unseen results are reported separately from the frozen 40-question E5 final benchmark,
whose authoritative strict semantic result remains **38/40 = 95.0%**.

## Evaluation stages

### U0/U1 — frozen-source preparation

- PDFs: **5/5**
- pages: **21**
- source SHA matches: **5/5**
- deterministic extraction success: **5/5**
- schema valid: **5/5**
- parser: `content-local-v2.1.6`

### U2 — unseen question set

- locked questions: **15**
- exactly three per PDF
- answerable: **14**
- abstention: **1**
- human verified: **15/15**
- question SHA-256: `603d3385f5d083aeabf071d8d0c9be88896d31eb3f6530e881efeb3c03baeb2d`

### U3/U4 — temporary-document condition

Human-approved result:

- PASS: **13**
- semantic FAIL: **1** (`U5Q-010`)
- technical failure: **1** (`U5Q-011`)
- semantic accuracy among successful responses: **92.86%**
- strict first-pass end-to-end success: **86.67%**

`U5Q-010` was attributed to temporary passage selection. `U5Q-011` was a persistent
DeepSeek empty-final-content technical failure.

### U5/U6 — isolated permanent ingestion

All technical safeguards passed:

- ingestion success: **5/5**
- deterministic record match: **5/5**
- source SHA match: **5/5**
- E4 append check: **5/5**
- E5-C row alignment: **5/5**
- exact duplicate rejection without mutation: **5/5**
- lifecycle decision recorded: **5/5**
- frozen E4 unchanged: **true**
- frozen E5-C unchanged: **true**
- normal incoming directory unchanged: **true**

The isolated derivative grew from **1,786 to 1,791 documents** and from **12,634 to 12,670 chunks**.

A strict compatibility gate reconstructed the five documents with the frozen E4 chunking policy
and obtained an exact **5/5 chunk-count and chunk-ID match**.

### U7 — post-ingestion E5-D + frozen Layer C

Retrieval on 14 answerable questions:

- Recall@1: **92.86%**
- Recall@3: **100%**
- Recall@5: **100%**
- MRR@5: **96.43%**
- nDCG@5: **97.36%**
- correct source@1: **100%**
- correct source+page@5: **100%**
- candidate source+page recall@20: **100%**

Human-approved hosted-QA result:

- semantic PASS: **13**
- semantic FAIL: **1**
- technical failure: **1**
- semantic accuracy among successful responses: **92.86%**
- strict primary end-to-end success: **86.67%**

## Failure attribution

### U5Q-010 — answer-bearing passage selection

The retrieval report gives a page-level hit because page 1 is represented in top-5. However, the
actual `Supersedure` and `Applicability` passages needed to answer the question are not in top-5.

This exposes an important evaluation lesson:

**correct-source/page retrieval does not always imply that the answer-bearing passage is available
to the generator.**

For safety-critical technical QA, passage-level support should therefore be audited in addition to
source/page recall.

### U5Q-011 — provider/structured-output reliability

In the post-ingestion condition, both approved U5Q-011 answer-bearing quotations are present in
top-5 evidence, yet DeepSeek returned empty final JSON content on the primary request and again on
the one exact retry.

This is attributed to provider/structured-output reliability rather than retrieval or document
understanding.

## Passage-support diagnostic

Across the 14 answerable U7 questions:

- any approved reference quote contained in top-5: **12/14 = 85.71%**
- all approved reference quotes contained in top-5: **8/14 = 57.14%**

These values are diagnostics, not replacement retrieval scores. Exact-string containment can be
false even when a semantically sufficient passage supports a correct response.

## Generalization conclusion

The held-out evaluation supports four conclusions:

1. **Deterministic ingestion generalizes reliably.** All five unseen PDFs were reproduced
   deterministically and admitted without mutating the frozen development artifacts.
2. **Duplicate and index-update safeguards behaved correctly.** Exact duplicate re-ingestion was
   rejected without state mutation for all five PDFs.
3. **E5-D retrieval generalized strongly after ingestion.** All 14 answerable questions had a
   correct source+page within top-5, and the correct source ranked first for every question.
4. **The remaining limitations are narrow but important.** One question exposed answer-bearing
   passage-selection weakness despite perfect page-level Recall@5, and one exposed persistent
   provider structured-output failure despite complete evidence.

## Final reporting table

| Evaluation condition | Retrieval | Human semantic result | Strict end-to-end |
|---|---|---|---|
| Frozen 40-question E5 final | Recall@5 35/36 = 97.22% | 38/40 PASS = 95.0% | 95.0% |
| Unseen temporary U3/U4 | Page Recall@5 14/14 = 100% | 13 PASS / 1 FAIL / 1 technical | 13/15 = 86.67% |
| Unseen post-ingestion U7 | E5-D Recall@5 14/14 = 100% | 13 PASS / 1 FAIL / 1 technical | 13/15 = 86.67% |

The 95.0% E5 final result remains the project’s authoritative final benchmark score. The unseen
results are separate post-final generalization evidence.

## Remaining engineering work

The evaluation phase is complete. Future engineering may improve:

- answer-bearing passage selection within long documents;
- lifecycle/correction normalization in Layer A;
- provider structured-output robustness and provider-independent fallback handling;
- user-facing aviation document assistant integration.

Any such changes occur **after** the frozen benchmark and unseen evaluation and must not rewrite
the preserved results above.
