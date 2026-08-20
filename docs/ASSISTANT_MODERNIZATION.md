# Aviation Assistant Modernization

Last updated: 20 August 2026

## Purpose

This is a **post-evaluation serving migration** for the Airbus EASA AD capstone. It improves the user experience and runtime behavior of the demonstrated assistant without replacing or retuning the frozen E5-C/E5-D retrieval methodology or Layer C evaluation contract.

## Accepted demo architecture

```text
Next.js App Router / React / TypeScript
Tailwind CSS 4 + shadcn-style UI
                |
                | typed HTTP + SSE
                v
FastAPI + Pydantic
                |
                +--> deterministic E5 query router
                |
                +--> frozen E5-C candidate generation
                |      BM25 + pinned Qwen embedding
                |
                +--> frozen E5-D reranker
                |      pinned Qwen reranker
                |
                +--> top-5 evidence emitted to UI
                |
                +--> streamed DeepSeek serving adapter
                       final JSON hidden until frozen
                       Layer C schema/citation validation
```

The modern FastAPI + Next.js stack is now the primary capstone demo runtime. The original dependency-light Python web UI remains as a fallback only.

## Performance change

The original live prototype launched separate embedding and reranker subprocesses for each question. Those workers loaded their models for that request and exited.

The modern serving path instead loads:

- `Qwen/Qwen3-Embedding-0.6B@97b0c61`;
- `Qwen/Qwen3-Reranker-0.6B@e61197e`;

once during FastAPI application lifespan startup. Both remain warm for subsequent questions.

Device policy:

```text
ASSISTANT_DEVICE=auto
→ MPS when supported
→ CPU fallback
```

The capstone demo uses one API worker and one ML concurrency slot to avoid duplicate model copies and competing MPS workloads.

## Research-integrity and performance acceptance

The compatibility gate was run locally on the seminar Mac using:

```bash
.venv/bin/python -m \
  full_corpus_pipeline.assistant_api.validate_warm_compatibility
```

Observed result:

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

Therefore:

- exact top-5 compatibility: **10/10 = 100%**;
- median retrieval latency decreased from **26.87 s** to **6.11 s**;
- measured median reduction: **77.26%**;
- predeclared 60% reduction target: **met**;
- serving device: **Apple MPS**.

This establishes that the warm serving refactor preserved the compatibility-set E5 top-5 output while materially improving local serving latency. It is a post-evaluation engineering result and is not merged into the frozen benchmark metrics.

## API

FastAPI endpoints:

```text
GET  /api/v1/health
GET  /api/v1/meta
POST /api/v1/query
POST /api/v1/query/stream
```

The browser primarily uses the SSE endpoint.

SSE event sequence:

```text
request.started
route.started
route.completed
retrieval.started
evidence.ready
generation.started
generation.progress ...
answer.completed
request.completed
```

No partial DeepSeek JSON is trusted or displayed as an answer. `generation.progress` contains only safe progress metadata. The final JSON is parsed and passed through the existing frozen Layer C schema and evidence-ID/citation validation before `answer.completed` is emitted.

If the provider returns empty or invalid final content, the result becomes `technical_error` and the retrieved source evidence remains visible.

## Frontend

Primary application:

```text
apps/web/
```

Key user experience:

- readiness indicator while Qwen models warm;
- four seminar-friendly example questions;
- retained multi-turn conversation;
- visible Route → Retrieve → Evidence → Answer stages;
- top-5 evidence displayed before Layer C completes;
- exact AD/page/section/source passage inspector;
- citation chips that jump to the corresponding evidence;
- explicit AD context chips for follow-up questions;
- Stop/cancel control;
- retrieval-only mode;
- conditions, compliance time and exceptions rendered separately;
- safety/authority boundary shown continuously.

Conversation history is a browser-session concern only. The full conversation is **not** silently injected into E5 retrieval. Follow-up document context is explicit and removable.

## Frontend/backend types

Pydantic schemas are exported by FastAPI OpenAPI.

Generate TypeScript declarations while FastAPI is running:

```bash
pnpm --dir apps/web generate:api
```

The REST health client uses `openapi-fetch`. The SSE event envelope remains a small explicit client because event streams are not ordinary JSON REST responses.

## Test stack

Python:

```text
unittest contract tests
warm E5 compatibility/latency gate
```

Frontend:

```text
TypeScript strict typecheck
ESLint
Vitest + Testing Library
Playwright smoke test
Next.js production build
```

## One-command demo

The accepted local demo starts with:

```bash
make demo
```

The launcher:

1. verifies the Python environment and pnpm;
2. prepares the serving snapshot if absent;
3. starts FastAPI;
4. waits until the warm models report `ready`;
5. starts Next.js;
6. shuts both down together on Ctrl+C.

The command was confirmed to work on the local MacBook Air.

Runtime URLs:

```text
API  http://127.0.0.1:8000
Web  http://127.0.0.1:3000
```

## Explicit non-goals

This migration does not introduce:

- LangChain;
- LlamaIndex;
- Pinecone/Qdrant/Chroma/pgvector;
- LLM query rewriting;
- a new embedding model;
- a new reranker;
- quantization;
- retrieval retuning;
- authentication/accounts;
- a conversation database;
- Redis;
- Kubernetes.

These would either change the evaluated retrieval methodology or add infrastructure unrelated to the capstone-demo objective.

## Frozen-result boundary

The authoritative benchmark remains:

```text
38/40 = 95.0% frozen E5 final semantic accuracy
35/36 = 97.22% frozen E5-D Recall@5
```

The modern assistant is an engineering layer built **after** those results were frozen. No serving outcome may overwrite the benchmark or unseen locks.

## Next work

The serving migration is accepted. Further work should focus on capstone-facing user experience and presentation evidence rather than retrieval retuning:

- representative live QA smoke tests;
- citation/evidence interaction checks;
- follow-up context behavior;
- error/abstention UX;
- final screenshots;
- architecture and performance figures for the final report and presentation.
