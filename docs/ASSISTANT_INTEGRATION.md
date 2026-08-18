# User-Facing Aviation Document Assistant Integration

## Status

**Post-evaluation engineering — assistant serving slice implemented.**

This integration is deliberately downstream of the frozen E5 final benchmark and the locked U0–U8 unseen evaluation. It reuses the validated retrieval/QA architecture for live questions but does not modify or reinterpret any benchmark result.

## Live architecture

```text
validated post-ingestion derivative
1,791 documents / 12,670 frozen-policy chunks
        ↓ non-destructive serving copy
 data_processed/serving/assistant_v1
        ↓
query router
 ├─ explicit AD identifier → known-document route
 └─ identifier-free query → discovery route
        ↓
E5-C candidate generation
BM25 + Qwen/Qwen3-Embedding-0.6B@97b0c61
        ↓ top 20
E5-D reranking
Qwen/Qwen3-Reranker-0.6B@e61197e
        ↓ top 5
Layer C
DeepSeek V4 Pro + frozen response contract
        ↓
answer / insufficient_evidence / conflicting_evidence / technical_error
        ↓
locally resolved AD + PDF + page + section citations
```

The assistant never receives private benchmark reference answers, target labels, human review decisions, or oracle evidence.

## 1. Prepare the serving snapshot

The live assistant does not read the evaluation derivative directly. First create a separate serving copy:

```bash
.venv/bin/python -m \
  full_corpus_pipeline.assistant.prepare_serving_snapshot
```

The preparation command:

1. runs the final unseen-generalization validator;
2. validates the post-ingestion 1,791-document / 12,670-chunk derivative;
3. verifies E5-C dense-row alignment;
4. copies the validated E4/E5-C artifacts to `data_processed/serving/assistant_v1/`;
5. verifies the copied file hashes against the validated source;
6. writes `data_processed/serving/assistant_v1/manifest.json`.

It refuses to overwrite an existing serving snapshot unless `--reset` is supplied. `--reset` only removes the serving snapshot directory; it never mutates the evaluation or frozen E5 source artifacts.

## 2. Run assistant contract tests

```bash
.venv/bin/python -m unittest discover \
  -s full_corpus_pipeline/tests \
  -p 'test_assistant_runtime.py'
```

These tests exercise evidence construction, citation presentation and the user-facing safety boundary without loading the large retrieval models.

## 3. Retrieval-only CLI demo

Use this first because it needs no DeepSeek request:

```bash
.venv/bin/python -m full_corpus_pipeline.assistant.cli \
  --retrieval-only \
  --show-evidence \
  "For EASA AD 2011-0041R1, what two actions had to be completed within 3 days after 14 March 2011?"
```

The result shows:

- routed query mode;
- top E5-D evidence;
- AD identifier;
- source PDF;
- page range;
- section;
- evidence ID.

## 4. Hosted-QA CLI demo

Ensure `DEEPSEEK_API_KEY` is present in the environment, then run:

```bash
.venv/bin/python -m full_corpus_pipeline.assistant.cli \
  "For EASA AD 2008-0008, what grace period applies above 20,000 flight cycles and what reporting is required?"
```

For machine-readable output:

```bash
.venv/bin/python -m full_corpus_pipeline.assistant.cli \
  --json \
  "For EASA AD 2008-0008, what grace period applies above 20,000 flight cycles and what reporting is required?"
```

If DeepSeek does not return a valid structured response, the live layer returns `status=technical_error` and keeps the retrieved evidence visible. It does not silently retry or substitute an uncited answer.

## 5. Local browser UI

Start the dependency-light local server:

```bash
.venv/bin/python -m full_corpus_pipeline.assistant.web
```

Open:

```text
http://127.0.0.1:8765
```

The UI provides:

- free-text question input;
- retrieval-only toggle;
- route display;
- answer/status display;
- conditions, compliance time and exceptions;
- page-cited evidence;
- full top retrieved passages;
- explicit safety boundary.

Health endpoint:

```text
GET /api/health
```

Query endpoint:

```text
POST /api/query
Content-Type: application/json

{
  "question": "...",
  "retrieval_only": false
}
```

The server binds to `127.0.0.1` by default and is intended for local capstone demonstration, not internet exposure.

## Serving behavior

### Known-document questions

If the user explicitly names an AD identifier, the existing deterministic router selects the known-document path. The AD identifier is used for routing but removed from passage-ranking behavior exactly as in the evaluated E5 architecture.

### Discovery questions

Identifier-free questions use the frozen E5-C discovery path with Qwen dense query encoding, BM25 fusion and the pinned E5-D reranker.

### Evidence depth

Layer C receives at most five reranked passages, matching the frozen E5-D evidence depth. The serving code does not increase evidence depth after observing benchmark or unseen failures.

### Citations

DeepSeek returns evidence IDs only. AD number, source PDF, page range and section are resolved locally from the retrieved evidence metadata. This prevents the hosted model from inventing source coordinates.

## Safety / reporting boundary

The live assistant is document decision support, not an aircraft-specific compliance authority.

Do not present it as:

- replacing the controlling EASA AD;
- replacing approved Airbus maintenance data;
- calculating operator-specific compliance deadlines without complete aircraft history;
- proving that every page-level retrieval hit contains the exact answer-bearing passage;
- changing the frozen 95.0% E5 final benchmark result.

Original EASA AD passages remain authoritative.

## Post-evaluation provenance

Everything under `full_corpus_pipeline/assistant/` and `data_processed/serving/` is **post-evaluation engineering**. The serving snapshot is derived from the already validated post-ingestion derivative, but it is not a new benchmark condition and must never be used to rewrite the frozen E5 or unseen locks.

## Next delivery step

After the local serving smoke test passes, the next capstone delivery task is to capture representative UI screenshots/results and integrate the finalized methodology, benchmark results, unseen-generalization findings and assistant architecture into the final report and presentation.
