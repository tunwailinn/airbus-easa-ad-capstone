# Agent Guide: Airbus EASA AD Capstone

Read this before changing code, data rules, experiments, or documentation.

Last updated: 18 August 2026

## Project boundary

- Frozen snapshot: **1,809 physical EASA AD PDFs / 1,808 base AD families**.
- Nominal development extraction: **1,804 PDFs**.
- Strict Airbus-only operational retrieval scope: **1,786 PDFs / 6,002 verified pages**.
- Five held-out PDFs completed the post-final unseen-document generalization/ingestion experiment.
- Scope filtering never deletes physical/source records.
- Detailed compliance interpretation uses original PDF passages, not normalized structured fields alone.

## Architecture

```text
Layer A — deterministic section-complete extraction
Layer B — verified original-PDF evidence + frozen E5-D retrieval
Layer C — frozen hosted evidence-grounded QA
```

## Current benchmark state — COMPLETE / LOCKED

Completed/frozen:

- parser v2.1.6 development + clean locked extraction test;
- page-text v1.1 source layer;
- E0/E4 historical retrieval;
- E5-A/B/C/D retrieval development;
- E5-D retrieval freeze;
- Layer C development + hosted-QA freeze;
- 40-question human-reviewed final benchmark;
- one-time primary final run + human semantic review;
- final oracle/reference-evidence diagnostic;
- five-PDF unseen preparation;
- 15-question unseen QA human review + lock;
- U3/U4 temporary-document unseen evaluation + human lock;
- U5/U6 isolated permanent-ingestion, duplicate and index safeguards;
- frozen E4 chunk-policy compatibility gate;
- U7 post-ingestion E5-D + Layer C run;
- U7 human semantic review + lock;
- U8 final unseen-generalization report + final completion lock.

Authoritative frozen E5 primary final result:

```text
38/40 = 95.0% strict semantic accuracy
35/36 = 97.22% retrieval Recall@5
```

Final unseen post-ingestion result:

```text
14/14 = 100% E5-D Recall@5 on answerable questions
14/14 = 100% correct source@1
13/14 = 92.86% semantic accuracy on successful responses
13/15 = 86.67% strict primary end-to-end success
U5Q-010 = Layer B post-ingestion passage-selection failure
U5Q-011 = provider/structured-output technical failure
```

The unseen result is separate from the frozen 40-question final benchmark.

Current next phase: **post-evaluation engineering, user-facing assistant integration, and final report/thesis delivery**.

## Non-negotiable rules

1. Source PDFs and immutable gold are read-only.
2. Keep one generated content record per physical PDF; operational scope is a separate filter.
3. Never merge passages or requirements from different PDF versions.
4. Keep lifecycle/latest-selection state outside content JSON.
5. Preserve Applicability, Definitions, Reason, Requirements/Compliance, Ref. Publications and Remarks wording when printed.
6. Do not normalize difficult compliance conditions, intervals, exceptions or terminating logic across the full corpus.
7. Original PDF passages remain authoritative for detailed compliance interpretation.
8. QA outputs must preserve source/page/section provenance through stable evidence metadata.
9. Abstain when supplied evidence is incomplete or conflicting.
10. Temporary upload and permanent ingestion never retrain models.
11. Confirmed external/mixed-holder records remain preserved but are excluded from the strict Airbus-only operational view.
12. Missing/malformed/unclassified holders are `unknown`, never automatic exclusions.
13. **Parser v2.1.6 is frozen. Do not modify it from locked-test, final, or unseen outcomes.**
14. The disclosed `2024-0038` extraction-test leak remains excluded from clean extraction scoring.
15. E0/E4 are frozen historical experiments and must not be retuned.
16. E5-D is the selected/frozen retrieval configuration and must not be retuned from development, final, or unseen misses.
17. Frozen E5-D candidate generation uses E5-C BM25 + `Qwen/Qwen3-Embedding-0.6B@97b0c61` over E4 section chunks.
18. Frozen E5-D reranking uses `Qwen/Qwen3-Reranker-0.6B@e61197e`, candidate limit 20 and final evidence depth 5.
19. Known-document AD identifiers are routing keys, not learned ranking features.
20. Discovery questions remain identifier-free and test corpus-wide discovery.
21. Hosted LLM use is allowed only at QA time.
22. Hosted-QA settings are frozen in `evaluation_sets/easa_airbus_ad_e5_benchmark_v1/hosted_qa_freeze.json`.
23. Semantic retries are prohibited for benchmark evaluation.
24. Exact transport retries are supplementary only, require identical question/evidence/prompt/config, and must have separate audit records.
25. Distinguish retrieval failures from Layer C reasoning/status failures and provider/transport failures.
26. Final E5 questions are immutable after the one-time final run.
27. The strict primary E5 result is **38/40 = 95.0%** and cannot be replaced by oracle/retry/unseen values.
28. `E5F-021` is a confirmed Layer B retrieval failure.
29. `E5F-011` remains a Layer C primary failure, specifically answer-selection/completeness sensitivity under retrieved evidence.
30. `E5F-040` is a status-calibration/run-to-run variability diagnostic, not a factual hallucination.
31. Original final oracle batch remains **39 successes / 1 technical failure**; the `E5F-035` retry is separate recovery evidence.
32. Oracle results are diagnostic only.
33. The five unseen PDFs must not be used to tune extraction, E5 retrieval, Layer C, evidence depth, or question design.
34. Unseen results are reported separately from the 40-question E5 final benchmark.
35. U0/U1 preparation is complete and immutable.
36. Unseen questions are human verified and locked at SHA-256 `603d3385f5d083aeabf071d8d0c9be88896d31eb3f6530e881efeb3c03baeb2d`.
37. U3 temporary primary is immutable and may not be rerun to replace its original output.
38. U3/U4 human-approved temporary result is **13 PASS / 1 semantic FAIL / 1 technical failure**.
39. `U5Q-001` is human-approved PASS; omission of dates is not material because its question did not request them.
40. `U5Q-010` is the only human-approved temporary and post-ingestion semantic failure; it is attributed to Layer B answer-bearing passage selection.
41. `U5Q-011` is a provider/structured-output failure. In U7, both approved answer-bearing passages were present, but the primary request and one exact post-ingestion retry both returned empty final content.
42. No further U5Q-011 evaluation retry is permitted or useful for the locked result.
43. U5/U6 permanent-ingestion safeguards passed **5/5** in an isolated store/index.
44. U5/U6 exact duplicate re-ingestion was rejected without mutation **5/5**.
45. The isolated post-ingestion derivative grew from **1,786 to 1,791 documents** and **12,634 to 12,670 chunks**.
46. Pre-U7 frozen E4 chunk-policy compatibility was **5/5 exact**.
47. U7 post-ingestion retrieval Recall@5 is **14/14 = 100%**, correct source@1 **14/14 = 100%**.
48. U7 human-approved result is **13 PASS / 1 semantic FAIL / 1 technical failure**; successful-response semantic accuracy is **13/14 = 92.86%** and strict primary success is **13/15 = 86.67%**.
49. Page-level Recall@5 is not sufficient proof that an answer-bearing passage reached Layer C. `U5Q-010` is the canonical counterexample.
50. Exact reference-quote containment is diagnostic only; it does not replace page-level retrieval metrics or human semantic review.
51. U7 human-review lock `evaluation_sets/unseen_incoming_5_v1/u7_post_ingestion_human_semantic_review_lock.json` is authoritative for U7.
52. Final unseen completion lock `evaluation_sets/unseen_incoming_5_v1/unseen_final_generalization_lock.json` is authoritative for U8.
53. **The evaluation phase is closed.** Any code/model/retrieval changes after 18 August 2026 are post-evaluation engineering and may not rewrite locked benchmark results.

## Frozen/active versions

- Content schema: `2.1.0`
- Parser: `content-local-v2.1.6`
- Extraction evaluator: `content-eval-v3.1.5`
- Scope audit: `corpus-scope-audit-v1.3`
- Page source: `page-text-v1.1`
- E0/E4 retrieval build: `rag-index-build-v1.2`
- E5 retrieval lock: `e5-retrieval-freeze-v1.0`
- E5-C embedding: `Qwen/Qwen3-Embedding-0.6B@97b0c61`
- E5-D reranker: `Qwen/Qwen3-Reranker-0.6B@e61197e`
- Hosted-QA adapter: `deepseek-direct-v1.1`
- Hosted-QA runner: `e5-hosted-qa-runner-v1.1`
- Hosted-QA prompt: `e5-hosted-qa-prompt-v1.0-dev`
- Hosted-QA response contract: `e5-hosted-qa-contract-v1.0`
- Hosted-QA freeze: `e5-hosted-qa-freeze-v1.0`
- Unseen preparation: `unseen-5-preparation-v1.0`
- Unseen question lock: `unseen-5-question-lock-v1.0`
- Unseen temporary runner: `unseen-5-temporary-qa-runner-v1.0`
- Unseen temporary evaluator: `unseen-5-temporary-qa-eval-v1.0`
- Unseen temporary human review: `unseen-5-temporary-human-semantic-review-v1.0`
- Unseen temporary result lock: `unseen-5-temporary-result-lock-v1.0`
- U5/U6 permanent-ingestion result lock: `unseen-5-permanent-ingestion-result-lock-v1.0`
- U7 post-ingestion runner: `unseen-5-post-ingestion-e5d-layer-c-runner-v1.0`
- U7 post-ingestion evaluator: `unseen-5-post-ingestion-qa-eval-v1.0`
- U7 human review: `unseen-5-u7-post-ingestion-human-semantic-review-v1.0`
- U7 human-review lock: `unseen-5-u7-post-ingestion-human-review-lock-v1.0`
- Final unseen lock: `unseen-5-final-generalization-lock-v1.0`
- Final unseen validator: `unseen-5-final-generalization-validator-v1.0`

## Key results

Extraction development primary (28): stable metadata F1 **0.9948**, applicability F1 **0.9929**, source containment **130/130**.

Clean extraction primary (17): stable metadata F1 **0.9831**, applicability F1 **0.9222**, source containment **74/74**.

E5-D development: Recall@5 **0.9630**, MRR@5 **0.8633**, nDCG@5 **0.8884**, known-document Recall@5 **1.0000**, discovery Recall@5 **0.8889**.

E5 primary final: 40/40 hosted success, retrieval Recall@5 **35/36 = 97.22%**, semantic accuracy **38/40 = 95.0%**.

Unseen U7 post-ingestion: retrieval Recall@5 **14/14 = 100%**, correct source@1 **14/14 = 100%**, semantic accuracy on successful responses **13/14 = 92.86%**, strict primary success **13/15 = 86.67%**.

## Unseen workflow

```text
U0 source/selection validation                 COMPLETE
U1 non-destructive preparation                 COMPLETE
U2 human-reviewed question lock                COMPLETE / LOCKED
U3 temporary retrieval + frozen Layer C        COMPLETE / PRESERVED
U4 temporary human review                      COMPLETE / LOCKED
U5 isolated permanent ingestion                COMPLETE / PASS
U6 duplicate/lifecycle/index safeguards        COMPLETE / PASS
U7 post-ingestion QA + human review             COMPLETE / LOCKED
U8 final unseen-generalization report           COMPLETE / LOCKED
```

Canonical unseen documentation:

```text
docs/UNSEEN_DOCUMENT_EVALUATION.md
docs/U8_FINAL_UNSEEN_GENERALIZATION_REPORT.md
```

Final validation command:

```bash
.venv/bin/python -m \
  full_corpus_pipeline.layer_c.validate_unseen_final_generalization
```

## Working protocol

Authority order:

1. current user request;
2. this file;
3. machine-readable retrieval/hosted-QA/final/unseen locks;
4. `docs/U8_FINAL_UNSEEN_GENERALIZATION_REPORT.md`;
5. `docs/UNSEEN_DOCUMENT_EVALUATION.md`;
6. `docs/E5_STATUS.md`;
7. `docs/LAYER_C_FINAL_EVALUATION.md`;
8. `docs/PROJECT_STATUS.md`;
9. `airbus_easa_ad_project_exact_plan.md`;
10. `docs/DECISIONS.md`;
11. `docs/BENCHMARK_DESIGN.md`.

Preserve unrelated artifacts, preserve first-pass failures, update documentation after material work, and never reopen frozen tuning from locked outcomes.
