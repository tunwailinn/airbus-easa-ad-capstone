# E5 Status

Last updated: 17 August 2026

## Current state

E5 development, retrieval selection, hosted-QA freeze, the one-time 40-question final benchmark, human semantic review, and the post-hoc oracle/reference-evidence diagnostic are complete.

**The authoritative primary final semantic result is 38/40 = 95.0%.**

The E5 result is frozen. No retrieval, prompt, provider/model, reasoning-effort, response-contract, evidence-depth, or final-question changes may be made from final-test or unseen observations. Oracle and unseen results are diagnostic/generalization results only and must not replace the primary score.

The project has now entered the separate five-PDF unseen-document evaluation:

- U0 source/selection validation: **complete**;
- U1 non-destructive preparation: **complete**;
- U2 unseen question drafting: **15 questions authored**;
- U2 human review: **pending, 0/15 verified**;
- U3 temporary hosted QA: **not started**;
- permanent ingestion: **not started**.

Detailed active protocol:

```text
docs/UNSEEN_DOCUMENT_EVALUATION.md
```

## Frozen E5 benchmark

- 24 development families / 16 final-test families;
- 60 human-reviewed development questions;
- 40 human-reviewed final questions;
- final questions SHA-256: `f6b008c1b5d24160cb5718e2d4e91a7e0d323277a531654e4b5c3a33995c9a85`;
- final composition: 36 answerable + 4 abstention/conflict;
- final query modes: 24 known-document + 12 identifier-free discovery + 4 abstention/conflict.

Frozen retrieval source remains `rag-index-build-v1.2`: **1,786 documents / 12,634 E4 section chunks**.

Machine-readable retrieval freeze:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/retrieval_freeze.json
```

Hosted-QA freeze:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/hosted_qa_freeze.json
```

Final benchmark lock:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/final_lock.json
```

## E5 retrieval development — COMPLETE / FROZEN

### E5-A

- overall Recall@5: **0.8889**;
- known-document Recall@5: **1.0000**;
- discovery Recall@5: **0.6667**;
- candidate source+page recall@20: **0.9444**.

### E5-B

- Recall@5: **0.9444**;
- discovery Recall@5: **0.8333**;
- candidate source+page recall@20: **0.9630**.

### E5-C

Pinned `Qwen/Qwen3-Embedding-0.6B@97b0c61` candidate generation raised candidate source+page recall@20 to **0.9815 (53/54)**.

### E5-D — selected retrieval configuration

Pinned reranker: `Qwen/Qwen3-Reranker-0.6B@e61197e`.

Frozen development result:

- Recall@1: **0.7963**;
- Recall@3: **0.9259**;
- Recall@5: **0.9630**;
- MRR@5: **0.8633**;
- nDCG@5: **0.8884**;
- correct source@5: **0.9815**;
- correct source+page@5: **0.9630**;
- candidate source+page recall@20: **0.9815**;
- known-document Recall@5: **1.0000 (36/36)**;
- discovery Recall@5: **0.8889 (16/18)**;
- routing accuracy: **1.0000**.

Development artifact:

```text
data_processed/evaluations/e5/e5d_development_evaluation.json
```

SHA-256:

```text
9241b5d777f47a95efd1a5afc9a4139d280be0a12c3b91b6eb2d44df31cbcb05
```

Do not retune against the remaining development misses `E5D-030` or `E5D-045`.

## Layer C hosted-QA configuration — FROZEN

Primary, oracle, and later unseen temporary-QA conditions must preserve the frozen generation configuration:

```text
provider: DeepSeek official API
adapter: deepseek-direct-v1.1
model: deepseek-v4-pro
thinking: enabled
reasoning_effort: high
max_tokens: 4096
prompt: e5-hosted-qa-prompt-v1.0-dev
runner: e5-hosted-qa-runner-v1.1
response contract: e5-hosted-qa-contract-v1.0
semantic retry: prohibited
```

The model sees only the question and supplied evidence. Private benchmark labels, reference answers, target AD labels, reference pages, category/query-mode labels, and answerability labels are not exposed during generation.

## One-time final benchmark — COMPLETE

### Frozen retrieval / automatic result

- hosted requests: **40/40 successful**;
- answerability/status accuracy: **1.0000**;
- Recall@1: **0.8333**;
- Recall@3: **0.9722**;
- Recall@5: **0.9722 (35/36)**;
- MRR@5: **0.8981**;
- nDCG@5: **0.9173**;
- correct source@5: **0.9722**;
- correct source+page@5: **0.9722**;
- known-document Recall@5: **1.0000 (24/24)**;
- discovery Recall@5: **0.9167 (11/12)**;
- reference-page citation hit rate: **0.9722**;
- target-AD citation hit rate: **0.9722**.

### Human semantic result

- semantic passes: **38/40**;
- semantic failures: **2/40**;
- strict end-to-end semantic accuracy: **95.0%**.

This **38/40 = 95.0%** is the authoritative primary final semantic result.

Primary failure interpretation:

1. `E5F-011` — correct target evidence was available, but the answer selected the wrong applicability detail. Primary classification: **Layer C answer-selection/completeness failure under retrieved evidence**.
2. `E5F-021` — correct `2018-0289R1` evidence was absent from frozen retrieval support and the answer selected `2025-0111`. Classification: **Layer B retrieval/candidate-generation failure**.

Approved diagnostics retained without changing the primary score:

- `E5F-015` — PASS, with a post-hoc lifecycle/benchmark ambiguity note;
- `E5F-030` — PASS, with a canonical reference-page citation diagnostic.

## Final oracle/reference-evidence diagnostic — COMPLETE

The oracle condition changed only the evidence source. The model/prompt/settings remained frozen.

Original oracle batch:

- selected: **40**;
- successful: **39**;
- technical/provider failures: **1** (`E5F-035`);
- request success rate: **0.9750**;
- answerability/status accuracy on successful requests: **0.9744**;
- reference-page citation hit rate: **1.0000**;
- target-AD citation hit rate: **1.0000**.

Key error-attribution results:

- `E5F-021` becomes correct with oracle evidence → **Layer B retrieval/candidate generation confirmed**;
- `E5F-011` becomes correct with focused oracle evidence → **Layer C evidence-selection/completeness sensitivity**;
- `E5F-040` changed answer state under unchanged negative-control evidence → **Layer C status-calibration/run-to-run variability**.

### E5F-035 exact transport retry

The original oracle request failed because DeepSeek returned empty JSON final content. One exact transport retry preserved the same question/evidence/prompt/config and recovered successfully.

The original 39-success/1-failure batch remains preserved. The retry is a separate diagnostic recovery artifact; do not rewrite the original run as 40/40.

## Reporting rule

Use these E5 values in reports:

- **Primary final end-to-end semantic accuracy: 95.0% (38/40)**;
- **Primary final retrieval Recall@5: 97.22% (35/36)**;
- **Known-document final Recall@5: 100% (24/24)**;
- **Discovery final Recall@5: 91.67% (11/12)**.

Oracle results are explanatory only. They must not replace or adjust the strict primary score.

## Unseen-document checkpoint — ACTIVE

Frozen unseen set:

```text
evaluation_sets/unseen_incoming_5_v1/
```

Five held-out cases:

- corrected: `2008-0008`;
- revised: `2011-0041R1`;
- supersedure: `2011-0142`;
- long document: `2026-0084`;
- simple original: `2007-0173`.

### U0/U1 complete

- source documents: **5/5**;
- source SHA-256 matches: **5/5**;
- pages: **21**;
- deterministic extraction successes: **5/5**;
- schema-valid records: **5/5**;
- parser: `content-local-v2.1.6`;
- hosted inference started: **false**;
- permanent ingestion started: **false**.

Preparation manifest SHA-256:

```text
e3a60433348003b8e238a6704d40ddcd6e389e4f7804df92057f4eec9bbadc05
```

### U2 draft authored, human review pending

A 15-question unseen QA draft has been authored, exactly 3 questions per held-out PDF.

Draft composition:

- identity/lifecycle: 4;
- applicability: 3;
- required action/compliance: 3;
- conditional/multi-passage: 3;
- referenced publication: 1;
- insufficient/conflict/abstention: 1.

Draft SHA-256:

```text
1d9600dd4379f501d0878adf6ae434076ef47ae0a299ef8be5bdc12cb55fc43b
```

Review state:

```text
human_verified: 0/15
needs_human_review: 15/15
```

The immediate gate is explicit human review and a locked unseen-question artifact. Do **not** run unseen hosted QA or permanent ingestion before that gate is complete.

After the lock:

1. run temporary-document retrieval + frozen Layer C QA;
2. preserve and human-review the temporary result;
3. only then run isolated permanent ingestion, duplicate/lifecycle/index-update safeguards, and post-ingestion QA;
4. report unseen results separately from the frozen E5 primary result.