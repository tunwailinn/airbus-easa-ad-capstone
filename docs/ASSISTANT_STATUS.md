# Aviation Document Assistant — Post-Evaluation Status

Last updated: 20 August 2026

## Current checkpoint

The modern assistant architecture has now passed the local serving acceptance gate on the seminar Mac and is the **primary capstone demo runtime**. The original dependency-light Python web UI remains available only as a fallback.

Implemented and locally accepted:

- Next.js App Router + React + TypeScript frontend under `apps/web/`;
- Tailwind CSS 4 + shadcn configuration and reusable UI primitives;
- multi-turn evidence-first aviation engineering UI with example prompts, pipeline state, citations, evidence inspector, retrieval-only mode, cancellation and explicit follow-up AD context;
- FastAPI + Pydantic serving API under `full_corpus_pipeline/assistant_api/`;
- one-time application lifespan loading for the exact pinned E5-C embedding model and E5-D reranker;
- MPS-preferred / CPU-fallback serving through the existing `choose_device()` policy;
- single ML-concurrency lane for a reliable seminar demo;
- bounded query-embedding and retrieval caches;
- SSE endpoint that exposes route/retrieval/evidence before hosted QA completes;
- separate post-evaluation DeepSeek streaming adapter that never emits reasoning content or unvalidated JSON fragments;
- final Layer C JSON is still validated against the frozen response schema and resolved evidence IDs before `answer.completed` is sent;
- OpenAPI-based frontend contract generation + `openapi-fetch` REST client;
- compatibility/latency gate comparing the original subprocess serving path against the warm path with exact top-5 chunk-ID equality;
- Vitest/Testing Library + Playwright test scaffolding;
- one-command demo launcher (`make demo` / `bash scripts/start_demo.sh`);
- separate `requirements-assistant.txt` so frozen evaluation dependencies/results remain untouched.

## Local warm-serving acceptance result

The compatibility validator was run locally on the MacBook Air with MPS and reported:

```text
version: assistant-warm-serving-compatibility-v1.0
question_count: 10
top5_exact_match_count: 10
top5_all_exact: true
legacy_median_retrieval_ms: 26873.7623
warm_median_retrieval_ms: 6110.1638
median_latency_reduction: 0.7726346
performance_target_60_percent_reduction_met: true
device: mps
```

Interpretation:

- exact E5 top-5 evidence compatibility: **10/10 = 100%**;
- legacy median retrieval latency: **26.87 s**;
- warm median retrieval latency: **6.11 s**;
- measured median latency reduction: **77.26%**;
- predeclared 60% reduction target: **met**;
- runtime device: **Apple MPS**.

`make demo` was also confirmed to start the modern FastAPI + Next.js application successfully on the same machine.

These are **post-evaluation serving measurements**. They do not alter or replace any frozen benchmark score.

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

The fallback must not be used as the primary seminar UI unless the modern serving runtime encounters an unexpected local failure.

## Research/evaluation boundary

This work is **post-evaluation serving engineering**. It does not change:

- frozen E5 final result: **38/40 = 95.0%**;
- frozen E5-D final Recall@5: **35/36 = 97.22%**;
- locked unseen U7 result: **13 PASS / 1 semantic FAIL / 1 technical failure**;
- frozen E5-C candidate logic;
- frozen E5-D model/revision/instruction;
- frozen Layer C prompt or response contract;
- any evaluation or unseen lock.

No LangChain, LlamaIndex, vector database, new embedding model, new reranker, quantization or retrieval retuning was introduced by this migration.

## Acceptance summary

The primary migration gate is now satisfied:

```text
top5_all_exact: true
performance_target_60_percent_reduction_met: true
make demo: works locally
```

Frontend acceptance already confirmed during the local migration process includes successful TypeScript checking, ESLint, Vitest unit testing after runner separation, and a successful Next.js production build. Playwright is maintained as the browser smoke-test layer.

## Next phase — capstone demo validation

Do not retune retrieval from this point for demo polish. The next work is user-facing validation and presentation preparation:

1. run representative known-document, discovery, lifecycle and abstention questions in the modern UI;
2. verify evidence appears before the final hosted answer and that citation chips open the intended passages;
3. verify explicit AD context on one follow-up question;
4. verify `technical_error` or abstention states preserve retrieved evidence;
5. capture final demo screenshots and measured latency for the final report/presentation;
6. use the modern assistant as the canonical system shown in final architecture diagrams.
