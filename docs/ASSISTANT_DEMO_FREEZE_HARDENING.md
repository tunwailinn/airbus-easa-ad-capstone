# Assistant Demo Freeze Hardening

Last updated: 20 August 2026

## Purpose

This document records the final reliability hardening applied **after** the accepted warm-serving migration and **after** the research evaluation was frozen.

The baseline serving acceptance remains:

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

These are serving-engineering measurements only. They do not replace or modify the frozen E5 benchmark.

## Hardening branch

```text
assistant-demo-freeze-hardening
```

The branch starts from the accepted modern UI/UX commit:

```text
3d7b6ca3c0fd104c8cbad25767733ab7e43d3611
```

## Changes

### 1. Follow-up scope is explicitly single-AD

The validated serving behavior routes a follow-up through one explicit AD context. Multi-document conversational context would be a new retrieval condition and is not introduced for the capstone demo.

The final contract therefore enforces:

```text
context_ad_numbers: 0 or 1 item
```

Client behavior:

- if older context selections are present, only the most recently selected AD is sent;
- the visible follow-up chip is replaced when a new AD is selected;
- the backend rejects requests containing more than one explicit context AD;
- normal questions that explicitly contain their own AD number still use the standard E5 query router.

This keeps follow-up routing deterministic and prevents the UI from changing the frozen retrieval methodology.

### 2. Incomplete SSE streams fail visibly

The browser now requires an `answer.completed` event before treating a live request as successful.

If the SSE connection closes early without a validated final answer:

```text
Assistant stream ended before a validated final answer was received.
```

The existing workspace error path restores the question to the composer so the user can retry or edit it.

This prevents a provider/network interruption from leaving the interface indefinitely in a misleading intermediate state.

### 3. Stop/cancellation has explicit stage semantics

The Stop button performs both:

```text
browser AbortController.abort()
+
POST /api/v1/query/{request_id}/cancel
```

Hosted DeepSeek streaming is actively interruptible through the request cancellation event.

Warm local retrieval now checks the same cancellation signal at safe boundaries:

```text
before retrieval
before/after discovery embedding
before/after candidate generation boundary
before/after reranking boundary
before evidence assembly return
```

Important limitation:

> An already-running PyTorch/MPS model kernel is not forcibly preempted. If Stop is pressed while embedding or reranking is inside a model call, that call may finish, but the request stops before the next retrieval stage begins.

This is intentional. Forcefully interrupting an in-flight model kernel would add substantial complexity and risk to a single-user seminar runtime without changing the research result.

### 4. Regression coverage

Backend contract tests now cover:

- safe request defaults;
- browser request IDs;
- one-AD follow-up context;
- rejection of multi-AD follow-up context;
- retrieval-only response contract;
- cached-payload immutability;
- retrieval cancellation checkpoints;
- cancellation endpoint signaling;
- interruption of blocked hosted-provider streaming.

Frontend unit tests now cover:

- newest-only explicit AD context normalization;
- visible single-document follow-up scope;
- successful `answer.completed` stream completion;
- failure when an SSE stream closes before a validated answer.

Playwright now covers:

- shell/evidence-inspector rendering;
- a deterministic mocked route → retrieval → evidence → answer flow;
- evidence and compliance information appearing in the UI;
- Stop restoring the active question;
- Stop calling the backend cancellation endpoint.

The browser tests do **not** call Qwen or DeepSeek. They test the application protocol and user experience deterministically.

### 5. Worktree-safe demo launcher

`scripts/start_demo.sh` now accepts an optional Python executable through:

```text
ASSISTANT_PYTHON
```

Normal single-checkout use remains unchanged:

```bash
make demo
```

For a Git worktree that shares the original project's virtual environment:

```bash
ASSISTANT_PYTHON=../Capstone/.venv/bin/python make demo
```

This avoids duplicating the virtual environment just to validate the hardening branch.

The launcher still requires the validated serving snapshot to be available from the current worktree path. For the hardening worktree, the accepted setup is a symlink for `data_processed/serving/assistant_v1` to the original project's validated serving snapshot.

## Required regression commands before merging

Run on the seminar Mac from project root:

```bash
.venv/bin/python -m unittest discover \
  -s full_corpus_pipeline/tests \
  -p 'test_assistant_api_contract.py'

pnpm --dir apps/web typecheck
pnpm --dir apps/web lint
pnpm --dir apps/web test
pnpm --dir apps/web build
pnpm --dir apps/web test:e2e
```

In a worktree sharing the original virtual environment, use:

```bash
../Capstone/.venv/bin/python -m unittest discover \
  -s full_corpus_pipeline/tests \
  -p 'test_assistant_api_contract.py'
```

Because `QueryRequest.context_ad_numbers` changed in the FastAPI schema, regenerate the frontend declarations while FastAPI is running:

```bash
.venv/bin/python -m full_corpus_pipeline.assistant_api.app
```

or, in the hardening worktree:

```bash
../Capstone/.venv/bin/python -m full_corpus_pipeline.assistant_api.app
```

Then in another terminal:

```bash
pnpm --dir apps/web generate:api
```

The generated declaration should be reviewed and committed if it changes.

## Mandatory retrieval compatibility recheck

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

Purpose: regression revalidation after final demo hardening.

The previously accepted **77.26%** latency reduction remains the canonical serving-performance result. The 84.49% figure above is an incidental hardening rerun and is not used to replace the controlled baseline.

Detailed machine-readable record:

```text
docs/ASSISTANT_HARDENING_REVALIDATION.json
```

## Final live smoke test

After all automated checks pass:

Normal checkout:

```bash
make demo
```

Hardening worktree sharing the original Python environment:

```bash
ASSISTANT_PYTHON=../Capstone/.venv/bin/python make demo
```

Validate the fixed showcase set in:

```text
docs/ASSISTANT_FINAL_DEMO_VALIDATION.md
```

## Research boundary

This hardening does not change:

- parser `content-local-v2.1.6`;
- frozen E5-C candidate-generation methodology;
- frozen E5-D model, revision or instruction;
- evidence depth of 5;
- frozen Layer C prompt/contract;
- frozen final benchmark results;
- locked unseen-generalization outcomes.

No benchmark score may be recomputed or rewritten from these demo-hardening changes.
