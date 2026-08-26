# Aviation Document Assistant — Post-Evaluation Status

Last updated: 26 August 2026

## Current checkpoint

The modern FastAPI + Next.js assistant is the **primary and demo-frozen capstone runtime**.

The final reliability hardening has been integrated into `main`, the post-hardening compatibility recheck passed, and the D1-D8 final live browser validation passed in full.

Frozen runtime baseline commit:

```text
88f96d5aca67fb0c98113f4f7b04410402a7e559
```

Commit message:

```text
merge: integrate assistant demo freeze hardening
```

This SHA is the recorded runtime freeze reference for the final capstone demo. Later documentation-only commits do not redefine the implemented retrieval or serving methodology.

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
make demo: works locally
```

Interpretation:

- exact top-5 evidence compatibility: **10/10 = 100%**;
- legacy median retrieval latency: **26.87 s**;
- warm median retrieval latency: **6.11 s**;
- measured median latency reduction: **77.26%**;
- predeclared 60% serving target: **met**.

These are post-evaluation serving measurements only. They do not replace or modify the frozen benchmark.

## Final hardening integrated

The final demo hardening adds three serving safeguards:

1. **single-AD follow-up scope** — only one explicit AD can be active for a follow-up;
2. **incomplete SSE detection** — the browser requires `answer.completed` before treating a streamed response as complete;
3. **safe cancellation checkpoints** — Stop interrupts hosted DeepSeek generation and prevents local retrieval from progressing beyond the next safe stage boundary.

An already-running PyTorch/MPS model kernel is not force-preempted. This is intentional for the single-user demo runtime.

Detailed implementation record:

```text
docs/ASSISTANT_DEMO_FREEZE_HARDENING.md
```

## Post-hardening compatibility recheck

The regression revalidation after hardening reported:

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

Purpose: verify that final demo hardening did not change normal top-5 retrieval behavior.

The previously accepted **77.26%** latency reduction remains the canonical serving-performance result. The 84.49% value above is an incidental revalidation run and is not used to replace the controlled baseline.

Machine-readable record:

```text
docs/ASSISTANT_HARDENING_REVALIDATION.json
```

## Final live demo acceptance

Validation date: **26 August 2026**.

All eight final live browser scenarios passed manual acceptance:

```text
D1 known-document compliance: PASS
D2 applicability: PASS
D3 corpus-wide discovery: PASS
D4 lifecycle relationship: PASS
D5 reference publication: PASS
D6 explicit follow-up context: PASS
D7 abstention / missing detail: PASS
D8 evidence-only mode: PASS
```

Additional required checks also passed:

```text
Stop/retry: PASS
Evidence inspector interactions: PASS
Focused frontend regression: 2 test files passed, 8 tests passed
```

The detailed acceptance record is:

```text
docs/D1_D8_FINAL_LIVE_DEMO_VALIDATION.md
```

This is **post-evaluation software acceptance**, not a research benchmark. Eight passing demo scenarios must not be reported as 100% research accuracy.

## Canonical modern implementation

```text
apps/web/
full_corpus_pipeline/assistant_api/
requirements-assistant.txt
scripts/start_demo.sh
Makefile
pnpm-workspace.yaml
```

Fallback prototype:

```text
full_corpus_pipeline/assistant/
```

The fallback remains contingency-only and is not the primary final interface.

## Research/evaluation boundary

All UI/UX, serving, cancellation and demo-hardening work is **post-evaluation engineering**. It does not change:

- frozen E5 final semantic result: **38/40 = 95.0%**;
- frozen E5-D final Recall@5: **35/36 = 97.22%**;
- locked unseen U7 outcome: **13 PASS / 1 semantic FAIL / 1 technical failure**;
- frozen E5-C candidate-generation methodology;
- frozen E5-D model/revision/instruction;
- frozen Layer C prompt/response contract;
- any parser, benchmark or unseen lock.

No LangChain, LlamaIndex, vector database, new embedding model, new reranker, quantization, query rewriting or retrieval retuning was introduced by final demo hardening.

## Demo freeze status

The final demo-freeze criteria are satisfied:

```text
automated regression checks passed
warm top-5 compatibility remained exact
D1-D8 manually reviewed and passed
no known citation/provenance mismatch remained
Stop/retry passed
make demo worked from the validated runtime
final runtime baseline SHA recorded
```

The assistant is therefore **demo-frozen**.

From this point, avoid UI, retrieval, model, prompt, or serving changes unless fixing a reproducible demo-blocking defect. Final work should focus on screenshots, the final architecture diagram, report/results discussion, and presentation/demo preparation.
