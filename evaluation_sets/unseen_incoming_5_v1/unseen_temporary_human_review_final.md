# Five-PDF Unseen Temporary QA — Human Semantic Review

**Review version:** `unseen-5-temporary-human-semantic-review-v1.0`  
**Review date:** 2026-08-17  
**Reviewer:** Tun Wai Linn  
**Status:** Human approved

## Final temporary-document result

- Questions: **15**
- First-pass hosted successes: **14**
- Persistent technical/provider failures: **1**
- Human semantic PASS: **13**
- Human semantic FAIL: **1**
- Semantic accuracy on successful responses: **13/14 = 92.86%**
- Strict first-pass end-to-end success: **13/15 = 86.67%**

This unseen result is separate from and does not change the frozen E5 primary final result.

## Human-approved decisions

### U5Q-001 — PASS

The earlier AI-assisted proposal marked this item as incomplete because the hosted answer omitted the correction date and the date of the superseded directive. After reviewing the wording of the actual question, that was too strict.

The question asks for:

1. what correction is identified;
2. which earlier directive is superseded; and
3. why the AD was republished.

The hosted answer supplies all three requested elements. It does **not** ask for either date, so omitting those dates is not a material error.

### U5Q-010 — FAIL — Layer B temporary passage selection

The page-level retrieval metric reported page 1 in the top five, but the post-hoc reference-quote containment diagnostic showed that neither approved answer-bearing page-1 quote (`Supersedure` nor `Applicability`) was actually present in the prompt evidence.

Therefore the Layer C `insufficient_evidence` response was reasonable for the evidence supplied. This is attributed to temporary passage selection, not generation.

### U5Q-011 — persistent technical/provider failure

The primary request failed because DeepSeek returned empty final JSON content. One exact transport retry was permitted. It used the identical question, evidence, prompt-payload SHA, provider/model, prompt, response contract, thinking mode, reasoning effort and token limit, and failed again.

No semantic result is assigned to U5Q-011. No further retry is permitted.

### Remaining 12 questions — PASS

The remaining successful responses were reviewed and approved as semantically consistent with the human-reviewed references and supplied evidence.

## Retrieval diagnostics

Frozen first-pass page-level metrics:

- any-reference-page Recall@5: **100%**
- full-reference-page coverage@5: **100%**

Post-hoc exact reference-quote containment diagnostic:

- any approved quote contained in top 5: **12/14 = 85.71%**
- all approved quotes contained in top 5: **8/14 = 57.14%**

The quote-containment values are attribution diagnostics only. They do not replace the frozen page-level retrieval metrics, because exact-string containment can fail even when a supplied passage semantically supports a correct answer.

## Reporting rule

Report the unseen temporary-document condition as:

- **92.86% human semantic accuracy among successful hosted responses (13/14)**;
- **86.67% strict first-pass end-to-end success (13/15)**;
- one semantic failure (`U5Q-010`, Layer B temporary passage selection);
- one persistent technical/provider failure (`U5Q-011`).

Do not merge these values into the frozen 40-question E5 final score and do not retune the frozen system from these held-out results.
