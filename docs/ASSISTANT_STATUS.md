# Aviation Document Assistant — Post-Evaluation Status

Last updated: 20 August 2026

## Current checkpoint

The modern FastAPI + Next.js assistant is the **primary capstone demo runtime**. Its warm-serving migration has already passed the local compatibility/performance gate on the seminar Mac.

Accepted warm-serving baseline:

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

## Final demo-hardening branch

Current reliability hardening is isolated on:

```text
assistant-demo-freeze-hardening
```

It starts from the accepted UI/UX revision:

```text
3d7b6ca3c0fd104c8cbad25767733ab7e43d3611
```

The branch adds three final safeguards before the demo is frozen:

1. **single-AD follow-up scope** — client sends only the most recently selected explicit AD and FastAPI rejects multi-AD context requests;
2. **incomplete SSE detection** — the browser now requires `answer.completed` and restores the question if a live stream closes early;
3. **safe retrieval cancellation checkpoints** — Stop interrupts DeepSeek immediately and prevents local retrieval from entering the next embedding/candidate/rerank stage after cancellation.

An already-running PyTorch/MPS kernel is not force-preempted. That limitation is explicit and intentional for the single-user seminar runtime.

Detailed hardening documentation:

```text
docs/ASSISTANT_DEMO_FREEZE_HARDENING.md
```

Final showcase/validation checklist:

```text
docs/ASSISTANT_FINAL_DEMO_VALIDATION.md
docs/ASSISTANT_DEMO_SHOWCASE_QUESTIONS.json
```

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

The fallback is retained for contingency only and is not the primary seminar interface.

## Research/evaluation boundary

All UI/UX, serving, cancellation and demo-hardening work is **post-evaluation engineering**. It does not change:

- frozen E5 final semantic result: **38/40 = 95.0%**;
- frozen E5-D final Recall@5: **35/36 = 97.22%**;
- locked unseen U7 outcome: **13 PASS / 1 semantic FAIL / 1 technical failure**;
- frozen E5-C candidate-generation methodology;
- frozen E5-D model/revision/instruction;
- frozen Layer C prompt/response contract;
- any parser, benchmark or unseen lock.

No LangChain, LlamaIndex, vector database, new embedding model, new reranker, quantization, query rewriting or retrieval retuning is introduced.

## Regression gate before merging the hardening branch

Run on the seminar Mac:

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

Regenerate FastAPI-derived frontend declarations while the backend is running:

```bash
.venv/bin/python -m full_corpus_pipeline.assistant_api.app
```

Then:

```bash
pnpm --dir apps/web generate:api
```

Rerun the compatibility validator:

```bash
.venv/bin/python -m \
  full_corpus_pipeline.assistant_api.validate_warm_compatibility
```

Required:

```text
top5_all_exact: true
```

Do not overwrite the accepted 77.26% latency baseline with an incidental rerun unless a new controlled serving measurement is intentionally being reported.

## Final demo-validation phase

After the automated regression gate passes:

```bash
make demo
```

Run the fixed D1-D8 showcase set in:

```text
docs/ASSISTANT_FINAL_DEMO_VALIDATION.md
```

Record only demo usability/provenance observations:

- route observed;
- evidence-first behavior;
- final status;
- citation/page correctness;
- total latency;
- PASS/FAIL notes.

This record must remain separate from frozen research evaluation metrics.

## Demo freeze

The assistant can be tagged as the final capstone demo release once:

```text
automated regression checks pass
warm top-5 compatibility remains exact
D1-D8 are manually reviewed
Stop/retry works
make demo works from a clean terminal
final screenshots are captured
```

After that point, avoid additional UI or serving changes unless they fix a reproducible demo-blocking defect. The next work should be final report, architecture diagram, results/discussion and presentation integration.
