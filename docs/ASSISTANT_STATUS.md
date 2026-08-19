# Aviation Document Assistant — Post-Evaluation Status

Last updated: 19 August 2026

## Current checkpoint

The original dependency-light assistant prototype remains available as a fallback, while the project now has the approved **modern capstone demo architecture** implemented on `main` and awaiting local acceptance on the seminar Mac.

Implemented:

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

## Canonical modern implementation

```text
apps/web/
full_corpus_pipeline/assistant_api/
requirements-assistant.txt
scripts/start_demo.sh
Makefile
pnpm-workspace.yaml
```

The original prototype remains at:

```text
full_corpus_pipeline/assistant/
```

It must not be removed until the warm compatibility gate and local UI acceptance pass.

## Research/evaluation boundary

This work is **post-evaluation serving engineering**. It does not change:

- frozen E5 final result: **38/40 = 95.0%**;
- frozen E5-D final Recall@5: **35/36 = 97.22%**;
- locked unseen U7 result: **13 PASS / 1 semantic FAIL / 1 technical failure**;
- frozen E5-C candidate logic;
- frozen E5-D model/revision/instruction;
- frozen Layer C prompt or response contract;
- any evaluation or unseen lock.

No LangChain, LlamaIndex, vector database, new embedding model, new reranker, quantization or retrieval retuning is introduced by this migration.

## Required local acceptance sequence

### 1. Pull and install

```bash
git pull

.venv/bin/pip install -r requirements-assistant.txt
pnpm install
```

`pnpm install` generates/updates `pnpm-lock.yaml`; commit that lockfile after the install succeeds.

### 2. Ensure the validated serving snapshot exists

```bash
.venv/bin/python -m \
  full_corpus_pipeline.assistant.prepare_serving_snapshot
```

If the snapshot already exists and is valid, do not replace it just to rerun this step.

### 3. Run Python contract tests

```bash
.venv/bin/python -m unittest discover \
  -s full_corpus_pipeline/tests \
  -p 'test_assistant_api_contract.py'
```

### 4. Mandatory research-integrity + performance gate

```bash
.venv/bin/python -m \
  full_corpus_pipeline.assistant_api.validate_warm_compatibility
```

Compatibility acceptance requires:

```text
top5_all_exact: true
```

The report also records legacy versus warm median retrieval latency and whether the predeclared 60% median reduction target is achieved. Performance is not claimed until this local measurement is run on the seminar Mac.

### 5. Start only the FastAPI backend and wait for `ready`

```bash
.venv/bin/python -m full_corpus_pipeline.assistant_api.app
```

In another terminal:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

The health response must report both Qwen models loaded.

### 6. Generate the real frontend OpenAPI declarations

With FastAPI still running:

```bash
pnpm --dir apps/web generate:api
```

This replaces the committed seed declarations with the exact schema exported by the running FastAPI application.

### 7. Frontend acceptance

```bash
pnpm --dir apps/web typecheck
pnpm --dir apps/web lint
pnpm --dir apps/web test
pnpm --dir apps/web build
```

Optional browser smoke test after the frontend is running:

```bash
pnpm --dir apps/web test:e2e
```

### 8. Full capstone demo

Stop any manually started backend/frontend processes, then run:

```bash
make demo
```

Expected runtime:

```text
FastAPI: http://127.0.0.1:8000
Next.js: http://127.0.0.1:3000
```

## Local acceptance boundary

The modernization code is implemented, but it is **not yet accepted as the primary seminar runtime** until the Mac run confirms:

- exact top-5 compatibility;
- successful Python/frontend static tests;
- successful Next.js production build;
- recorded before/after retrieval latency;
- clean end-to-end browser QA using both known-document and discovery examples.

Until then, the old Python web UI remains the fallback.
