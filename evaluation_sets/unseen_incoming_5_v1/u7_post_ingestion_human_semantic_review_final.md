# U7 Post-Ingestion E5-D + Layer C — Human Semantic Review

**Review version:** `unseen-5-u7-post-ingestion-human-semantic-review-v1.0`  
**Review date:** 2026-08-18  
**Reviewer:** Tun Wai Linn  
**Status:** Human approved and locked

## Final U7 primary result

- Questions: **15**
- Hosted successes: **14**
- Hosted technical failures: **1**
- Human semantic PASS: **13**
- Human semantic FAIL: **1**
- Semantic accuracy among successful responses: **13/14 = 92.86%**
- Strict primary end-to-end success: **13/15 = 86.67%**

## Post-ingestion retrieval

On the 14 answerable questions:

- Recall@1: **13/14 = 92.86%**
- Recall@3: **14/14 = 100%**
- Recall@5: **14/14 = 100%**
- MRR@5: **96.43%**
- nDCG@5: **97.36%**
- Correct source@1: **14/14 = 100%**
- Correct source+page@5: **14/14 = 100%**
- Candidate source+page recall@20: **14/14 = 100%**

The five ingested PDFs match the frozen E4 chunking policy exactly, 5/5.

## Human-approved exception decisions

### U5Q-010 — FAIL — Layer B post-ingestion passage selection

Although page 1 is represented in the top-five retrieval result, neither approved answer-bearing
`Supersedure` nor `Applicability` quotation is present in the top-five prompt evidence. The
answer-bearing applicability chunk ranks outside the final evidence depth.

The hosted `insufficient_evidence` response is therefore reasonable for the evidence supplied.
This is a Layer B passage-selection failure, not a Layer C reasoning failure.

This case demonstrates that **page-level Recall@5 can overstate answer-bearing passage support**.

### U5Q-011 — TECHNICAL FAILURE — provider/structured output

Both approved U5Q-011 source quotations are present in the post-ingestion top-five evidence.
Nevertheless, the frozen DeepSeek request returned:

`DeepSeek JSON Output returned empty final content`

The single exact post-ingestion transport retry reused the identical question, evidence,
prompt-payload SHA, provider/model, prompt, response contract, reasoning settings and token limit,
without rerunning retrieval. It failed with the same error.

No semantic result is assigned to U5Q-011.

## Remaining 13 questions — PASS

The human reviewer approved the remaining 13 responses as correct for the requested scope and
supported by the supplied evidence.

Exact normalized reference-quote containment remains diagnostic only. In particular, U5Q-014 and
U5Q-015 are semantically correct despite exact-quote-containment misses.

## Reporting boundary

U7 is a post-final unseen-document generalization result. It does **not** replace or modify the
frozen 40-question E5 final result of **38/40 = 95.0% strict semantic accuracy**.

No U7 result may be used to retrospectively retune the frozen parser, E5-C/E5-D retrieval stack,
prompt, DeepSeek model/settings, response contract or evidence depth.
