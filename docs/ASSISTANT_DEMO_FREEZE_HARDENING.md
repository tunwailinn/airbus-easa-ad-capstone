# Assistant Demo Freeze Hardening

Publication labels: E1 = legacy E4; E2-A–D = legacy E5-A–D. Artifact names, question IDs and code excerpts retain their original labels. See [experiment label mapping](EXPERIMENT_LABELS.md).

Last updated: 27 August 2026

## Purpose

This document records the final reliability hardening applied **after** the accepted warm-serving migration and **after** the research evaluation was frozen.

The hardening work is complete, merged into `main`, revalidated for exact retrieval compatibility, and covered by the final D1-D8 live browser acceptance.

This is a historical implementation/acceptance record. It is not a new research benchmark.

## Frozen runtime baseline

The hardening branch was integrated into `main` by:

```text
88f96d5aca67fb0c98113f4f7b04410402a7e559
merge: integrate assistant demo freeze hardening
```

This SHA is the frozen runtime baseline for the final capstone demo.

The hardening branch was:

```text
assistant-demo-freeze-hardening
```

and originally started from the accepted modern UI/UX commit:

```text
3d7b6ca3c0fd104c8cbad25767733ab7e43d3611
```

Later documentation-only commits do not redefine the implemented retrieval or serving methodology.

## Accepted warm-serving baseline

```text
question_count: 10
top5_exact_match_count: 10
top5_all_exact: true
legacy_median_retrieval_ms: 26873.7623
warm_median_retrieval_ms: 6110.1638
median_latency_reduction: 77.26%
performance_target_60_percent_reduction_met: true
device: mps
```

Interpretation:

- exact top-5 evidence compatibility: **10/10 = 100%**;
- legacy median retrieval latency: **26.87 s**;
- warm median retrieval latency: **6.11 s**;
- canonical measured latency reduction: **77.26%**;
- predeclared 60% serving target: **met**.

These are serving-engineering measurements only. They do not replace or modify the frozen E2 benchmark.

## Implemented hardening

### 1. Follow-up scope is explicitly single-AD

The validated serving behavior routes a follow-up through one explicit AD context. Multi-document conversational context would be a new retrieval condition and was not introduced for the capstone demo.

The final contract enforces:

```text
context_ad_numbers: 0 or 1 item
```

Final behavior:

- only the most recently selected AD is sent as explicit context;
- the visible follow-up chip is replaced when a new AD is selected;
- FastAPI rejects requests containing more than one explicit context AD;
- questions that explicitly contain their own AD number still use the standard E2 query router.

This keeps follow-up routing deterministic and avoids changing the frozen retrieval methodology.

### 2. Incomplete SSE streams fail visibly

The browser requires an `answer.completed` event before treating a live request as successful.

If a stream closes before a validated final response:

```text
Assistant stream ended before a validated final answer was received.
```

The question is restored to the composer so the user can retry or edit it. Partial DeepSeek JSON is never surfaced as an authoritative answer.

### 3. Stop/cancellation has explicit stage semantics

The Stop control performs both:

```text
browser AbortController.abort()
+
POST /api/v1/query/{request_id}/cancel
```

Hosted DeepSeek streaming is actively interruptible through the request cancellation event.

Warm local retrieval checks the same cancellation signal at safe boundaries around:

```text
retrieval start
discovery embedding
candidate generation
reranking
evidence assembly return
```

Important limitation:

> An already-running PyTorch/MPS model kernel is not forcibly preempted. If Stop is pressed while embedding or reranking is inside a model call, that call may finish, but the request stops before advancing beyond the next safe stage boundary.

This is intentional for the single-user capstone demo runtime.

### 4. Regression coverage

Backend contract tests cover:

- safe request defaults;
- browser request IDs;
- one-AD follow-up context;
- rejection of multi-AD context;
- retrieval-only response contract;
- cached-payload immutability;
- retrieval cancellation checkpoints;
- cancellation endpoint signaling;
- interruption of blocked hosted-provider streaming.

Frontend tests cover:

- newest-only explicit AD context normalization;
- visible single-document follow-up scope;
- successful `answer.completed` stream completion;
- failure when an SSE stream closes before a validated answer;
- cancellation;
- keyboard and pointer evidence-panel resizing;
- reset behavior;
- Reader/Raw mode;
- passage copy behavior.

Playwright covers the deterministic application protocol/UI flow without loading Qwen or calling DeepSeek in the browser test harness.

The focused frontend regression result recorded after live validation was:

```text
Test Files  2 passed (2)
Tests       8 passed (8)
```

### 5. Worktree-safe demo launcher

`scripts/start_demo.sh` accepts an optional Python executable through:

```text
ASSISTANT_PYTHON
```

Normal single-checkout use:

```bash
make demo
```

Validated worktree use:

```bash
ASSISTANT_PYTHON=../Capstone/.venv/bin/python make demo
```

The hardening worktree reused the original validated serving snapshot through a symlink for:

```text
data_processed/serving/assistant_v1
```

This avoided duplicating the virtual environment or large serving assets during acceptance testing.

## Completed regression gate

Before freeze, the following gate was completed successfully:

```text
backend assistant API contract tests: PASS
TypeScript: PASS
ESLint: PASS
Vitest: PASS
Next.js production build: PASS
Playwright: PASS
warm-serving compatibility recheck: PASS
make demo: PASS
```

FastAPI-derived frontend declarations were regenerated and committed as part of the final merged state.

## Post-hardening retrieval compatibility recheck

The post-hardening compatibility recheck passed on 20 August 2026:

```text
question_count: 10
top5_exact_match_count: 10
top5_all_exact: true
legacy_median_retrieval_ms: 38903.5944
warm_median_retrieval_ms: 6034.8178
median_latency_reduction: 84.49%
performance_target_60_percent_reduction_met: true
device: mps
```

Purpose: confirm that the final demo hardening did not change normal top-5 retrieval behavior.

The previously accepted **77.26%** latency reduction remains the canonical serving-performance result. The 84.49% figure is an incidental hardening revalidation run and does not replace the controlled baseline.

Machine-readable record:

```text
docs/ASSISTANT_HARDENING_REVALIDATION.json
```

## Final live demo acceptance

The live browser acceptance was completed on **26 August 2026**.

```text
D1 known-document compliance: PASS
D2 applicability: PASS
D3 corpus-wide discovery: PASS
D4 lifecycle relationship: PASS
D5 reference publication: PASS
D6 explicit follow-up context: PASS
D7 abstention / missing procedure detail: PASS
D8 evidence-only mode: PASS
Stop/retry: PASS
Evidence inspector interactions: PASS
```

Detailed record:

```text
docs/D1_D8_FINAL_LIVE_DEMO_VALIDATION.md
```

Final synchronized checklist:

```text
docs/ASSISTANT_FINAL_DEMO_VALIDATION.md
```

Machine-readable showcase record:

```text
docs/ASSISTANT_DEMO_SHOWCASE_QUESTIONS.json
```

Eight passing demo scenarios must not be reported as 100% research accuracy.

## Research boundary

This hardening does not change:

- parser `content-local-v2.1.6`;
- frozen E2-C candidate-generation methodology;
- frozen E2-D model, revision or instruction;
- evidence depth of 5;
- frozen Layer C prompt/contract;
- frozen final benchmark results;
- locked unseen-generalization outcomes.

No benchmark score is recomputed or rewritten from these demo-hardening changes.

## Freeze status

The runtime/code freeze is complete:

```text
hardening merged into main: PASS
warm top-5 compatibility remained exact: PASS
D1-D8 live acceptance: PASS
Stop/retry: PASS
Evidence inspector checks: PASS
frozen runtime SHA recorded: PASS
```

The assistant is **demo-frozen**.

Screenshots, architecture diagrams, report writing, and presentation preparation are post-freeze presentation assets. They do not alter the frozen runtime unless a reproducible demo-blocking defect requires a targeted fix.
