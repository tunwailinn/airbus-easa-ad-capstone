# Five-PDF Unseen Post-Ingestion QA — Proposed Semantic Review

**Review version:** `unseen-5-post-ingestion-semantic-review-proposed-v1.0`  
**Review date:** 2026-08-18  
**Status:** AI-assisted proposal pending explicit human approval

This document records the proposed semantic interpretation of U7. It is **not** a human-reviewed result until the reviewer explicitly approves or revises these judgments. The frozen 40-question E5 final benchmark and the locked U3/U4 temporary-document result remain unchanged.

## Bound U7 artifacts

- chunk-policy compatibility SHA-256: `6e32ffc76fdf9cdbe8d470d23f510b09eecad6d29f9d95852f5834a3d5d8c3fb`
- U7 run summary SHA-256: `032f39a8671d03e3c71ee223c41ec41e97a27f62984e74bde8939249629649e1`
- U7 retrieval report SHA-256: `a1e2c5e76776dcbc8ddab5131cb549bc11ae9d052481f6da0b035674a7031c86`
- automatic evaluation SHA-256: `12bc383d9323908a6f7f0e61c0b0372c746d5c8d279e56a8b1e2e013ec8fb4ca`
- reference-quote diagnostic SHA-256: `779fa90b30f50353959ba85f126c349f9803ede40778cc691951ecc4e681357c`
- review packet SHA-256: `e5875a1d6525e159f3e8b5a395a79bfe36095fea9cf497d74afddce25d4f743c`

## Automatic U7 result

- questions: **15**;
- answerable: **14**;
- abstention: **1**;
- hosted successes: **14/15 = 93.33%**;
- hosted failures: **1/15**;
- answerability/status accuracy on successful requests: **13/14 = 92.86%**;
- post-ingestion E5-D Recall@1: **13/14 = 92.86%**;
- Recall@3: **14/14 = 100%**;
- Recall@5: **14/14 = 100%**;
- MRR@5: **0.9643**;
- nDCG@5: **0.9736**;
- correct source@1: **14/14 = 100%**;
- correct source+page@5: **14/14 = 100%**;
- candidate source+page recall@20: **14/14 = 100%**;
- any approved quote contained in top 5: **12/14 = 85.71%**;
- all approved quotes contained in top 5: **8/14 = 57.14%**;
- reference-page citation hit among applicable successful answerable responses: **12/13 = 92.31%**;
- target-AD citation hit among applicable successful answerable responses: **12/13 = 92.31%**.

All 15 post-ingestion queries routed as `known_document`, because the AD identifiers are explicitly present in these locked unseen questions after permanent ingestion. The original `temporary_document` authoring mode is provenance only.

## Proposed semantic outcome

- semantic PASS: **13**;
- semantic FAIL: **1**;
- technical/provider failure: **1**;
- proposed semantic accuracy among successful hosted responses: **13/14 = 92.86%**;
- proposed strict first-pass end-to-end success: **13/15 = 86.67%**.

## Proposed decisions

### U5Q-001 — PASS

The question asks what correction is identified, which earlier directive is superseded, and why the AD was republished. The hosted answer supplies those requested elements. As in the already human-approved U4 judgment, omission of the correction date and superseded-directive date is not material because the question does not ask for those dates.

### U5Q-002 — PASS

The hosted answer correctly lists A310-221, -222, -322, -324 and -325, all serial numbers, and correctly states the production-modification No. 10149 exclusion.

### U5Q-003 — PASS

The answer correctly gives the 500-FC grace period for aircraft above 20,000 FC, preserves the revision-02/03 constraint, and states the 30-day reporting requirement including no-findings reports.

### U5Q-004 — PASS

The answer correctly identifies EASA Emergency AD 2011-0041-E dated 10 March 2011 and both effective dates: 07 October 2014 for Revision 1 and 14 March 2011 for the original issue.

### U5Q-005 — PASS

The answer correctly gives both concurrent actions, the Airbus AOT identifier, AFM TR 83/84, the 3-day timing and the thereafter-operation requirement.

### U5Q-006 — PASS

The answer correctly preserves both paragraph (3) branches for AFM-TR removal and the additional Airbus MSB A380-31-8071 condition that makes paragraph (1.1) no longer applicable.

### U5Q-007 — PASS

The answer correctly identifies EASA AD 2006-0280 and the accepted AFM incorporation methods. The additional statement that later approved revisions of AFM TR112 are acceptable is source-supported. The question does not ask for the 10-day compliance time, so omission of that time from the prose answer is not a failure.

### U5Q-008 — PASS

The answer correctly resolves the contrast asked by the question: the new DISPLAY UNIT FAILURE procedure is not limited to the earlier engine serial-number batch and applies broadly to the listed A318/A319/A320/A321 applicability, all manufacturer serial numbers. No material requested condition is omitted.

### U5Q-009 — PASS

The generator action and the follow-on actions if the display units stop flashing are complete and consistent with Appendix 1.

### U5Q-010 — FAIL — Layer B post-ingestion passage selection

The question asks which AD is superseded by EASA AD 2026-0084 and which exact A340 models are covered. The model returned `insufficient_evidence`.

Although post-ingestion page-level retrieval scored this item as a source+page hit because a page-1 `Document` chunk was ranked second, the supplied top-5 passages did **not** contain either approved answer-bearing quote. The exact `Applicability` chunk was outside the top five, and no top-five passage supplied the supersedure statement. Therefore the model's abstention is reasonable for the evidence it actually received.

Attribution: **Layer B post-ingestion passage selection / reranking**, not Layer C hallucination.

This is an important limitation of page-overlap Recall@5: the correct page can be present while the answer-bearing section from that page is absent.

### U5Q-011 — TECHNICAL FAILURE — provider/structured output

The U7 request again failed with:

```text
DeepSeek JSON Output returned empty final content
```

U7 prompt payload SHA-256:

```text
7a85360c8bfcb9bf9dff5f2932d6381e75b3bb740a8b271192501143c634ba5b
```

This is a **different post-ingestion evidence payload** from the earlier temporary-document payload, yet the provider produced the same empty-final-content failure pattern.

Crucially, U7 retrieval supplied both approved answer-bearing passages in top five:

- page 10 / EV1 contains Action 12, Group 43A pre-mod 40556 and pre-mod 202584, SB A340-53-4197 (Mod 202584), LR 10,400 FC / 71,000 FH and SR 12,200 FC / 51,600 FH;
- page 7 / EV5 contains the Table 3 header defining the LR/SR columns and `FC or FH, whichever occurs first`.

Therefore the U7 failure is **not attributable to missing evidence**. It is classified as a provider/structured-output failure. No semantic result is assigned.

### U5Q-012 — PASS

The answer correctly preserves the pre-14-October-2019 condition, outside-Window-of-Embodiment condition, 30-day Airbus-contact requirement and follow-on compliance with Airbus instructions.

### U5Q-013 — PASS

Both A310 and A300-600 applicability exclusion branches are reproduced correctly.

### U5Q-014 — PASS

The exact-string quote-containment diagnostic reports no full approved quote match, but the top-five evidence includes the Ref. Publications chunk stating `SB A310-53-2126 original issue; and SB A300-53-6156 original issue, or later approved revisions of these documents.` The hosted answer is therefore semantically and citation-supported. This is an example of why the exact-string diagnostic is attribution-only and cannot by itself determine semantic correctness.

### U5Q-015 — PASS

The model correctly abstains from inventing fastener dimensions, quantities, torque values or a step-by-step reinforcement procedure. It correctly states that those details require the referenced Service Bulletin instructions.

## Comparison with U3/U4 temporary-document condition

The proposed semantic totals are numerically unchanged from the human-approved temporary result: 13 PASS, 1 semantic FAIL and 1 technical failure. However, the post-ingestion retrieval condition is stronger:

- E5-D source+page Recall@5 is **100%**;
- correct source@1 is **100%**;
- candidate source+page recall@20 is **100%**;
- U5Q-011 has complete answer-bearing evidence in top five, so its failure is clearly isolated to the provider/output layer;
- U5Q-010 remains a passage-selection miss despite page-level source+page success, showing that passage-level evidence diagnostics remain necessary.

## Human approval boundary

These judgments must not be labelled `human_reviewed`, `human_verified`, or locked until the reviewer explicitly approves or revises them. After approval, create the final U7 human-review record/lock and then produce U8 final unseen-generalization reporting.
