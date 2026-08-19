# Aviation Document Assistant — Post-Evaluation Status

Last updated: 19 August 2026

## Current checkpoint

The original dependency-light assistant prototype remains available as a fallback, but the project is now migrating to the approved **modern capstone demo architecture**.

Implemented in the modernization branch of `main`:

- Next.js App Router + React + TypeScript frontend under `apps/web/`;
- Tailwind CSS 4 + shadcn configuration and component-ready structure;
- evidence-first aviation engineering UI with example prompts, pipeline state, citations, evidence inspector, retrieval-only mode, cancellation and explicit follow-up AD context;
- FastAPI + Pydantic serving API under `full_corpus_pipeline/assistant_api/`;
- one-time application lifespan loading for the exact pinned E5-C embedding model and E5-D reranker;
- MPS-preferred / CPU-fallback serving through the existing `choose_device()` policy;
- single ML-concurrency lane for a reliable seminar demo;
- bounded query-embedding and retrieval caches;
- FastAPI SSE endpoint that exposes routing/evidence before hosted QA completes;
- separate post-evaluation DeepSeek streaming adapter that never emits reasoning content or unvalidated JSON fragments;
- final Layer C JSON is still validated against the frozen response schema and resolved evidence IDs before `answer.completed` is sent;
- compatibility/latency gate comparing the original subprocess serving path against the warm path with exact top-5 chunk-ID equality;
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

```bash
git pull

.venv/bin/pip install -r requirements-assistant.txt
pnpm install

# Ensure the validated post-ingestion serving snapshot exists.
.venv/bin/python -m full_corpus_pipeline.assistant.prepare_serving_snapshot

# Mandatory research-integrity + performance gate.
.venv/bin/python -m \
  full_corpus_pipeline.assistant_api.validate_warm_compatibility

# Frontend static checks.
pnpm --dir apps/web typecheck
pnpm --dir apps/web lint
pnpm --dir apps/web build

# Generate the frontend API declarations while FastAPI is running.
pnpm --dir apps/web generate:api

# Full demo.
make demo
```

Compatibility acceptance requires:

```text
top5_all_exact: true
```

The report also records legacy versus warm median retrieval latency and whether the predeclared 60% median reduction target is achieved. Performance is not claimed until this local measurement is run on the seminar Mac.

## Expected demo runtime

```text
FastAPI: http://127.0.0.1:8000
Next.js: http://127.0.0.1:3000
```

The API health endpoint should report both Qwen models loaded before the frontend enables questioning.

## Next step

Run the local acceptance sequence above. If top-5 compatibility passes, use the modern UI as the primary capstone demo and keep the old Python web UI only as a fallback. If compatibility fails, fix serving equivalence before using the new warm inference path in the seminar.
