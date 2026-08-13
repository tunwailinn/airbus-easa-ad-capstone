# Layer C — Hosted Evidence-Grounded QA

## Status

Frozen E5-D retrieval remains unchanged.

**Phase C3 development selection and the oracle/reference-evidence comparison are complete. Phase C4 hosted-QA freeze tooling is implemented; the next action is to generate, validate, and commit `hosted_qa_freeze.json`.**

The 16 final-test families and 40 final questions remain sealed until that freeze is committed and validates successfully.

Detailed records:

```text
docs/LAYER_C_DEVELOPMENT_EVALUATION.md
docs/LAYER_C_ORACLE_EVIDENCE.md
docs/LAYER_C_ORACLE_EVALUATION.md
```

## Production boundary

```text
Question
→ frozen E5-D retrieval
→ frozen top-5 original-PDF evidence
→ DeepSeek V4 Pro
→ local response-contract validation
→ local EV citation resolution
→ cited answer or evidence-based abstention
```

Layer C may not retune routing, candidate generation, embedding/reranker models, RRF settings, candidate depth, reranker instruction, chunking, or evidence depth.

## Selected hosted-QA configuration

```text
provider: DeepSeek official API
provider adapter: deepseek-direct-v1.1
model: deepseek-v4-pro
thinking: enabled
reasoning_effort: high
max_tokens: 4096
temperature: not used in thinking mode
prompt: e5-hosted-qa-prompt-v1.0-dev
hosted QA runner: e5-hosted-qa-runner-v1.1
response contract: e5-hosted-qa-contract-v1.0
production evidence: frozen E5-D top 5
evidence pack: e5-evidence-pack-v1.0
evidence depth: 5
```

No development finding justified changing this configuration after the retrieved/oracle comparison.

DeepSeek `reasoning_content` is ignored and never persisted. Only final JSON output, usage metadata, request ID, and locally resolved citations are stored.

## Response contract

Machine-readable schema:

```text
full_corpus_pipeline/layer_c/hosted_qa_contract.schema.json
```

Allowed states:

- `answered`
- `insufficient_evidence`
- `conflicting_evidence`

An answered result must cite supplied evidence IDs. Abstention states require a non-empty reason. Returned EV identifiers are resolved locally to AD/PDF/page/section metadata.

## No benchmark leakage

Model-visible payload contains only:

```text
question_id
question
evidence
```

Private fields remain outside hosted inference:

- category;
- query mode;
- answerability label;
- target AD;
- reference pages;
- retrieval labels/ranks; and
- human reference answers.

## Retrieved-evidence development result

The full 60-question development run used the selected configuration.

First pass:

```text
hosted successes: 59
hosted failures: 1
first-pass hosted completion: 59/60 = 98.3%
```

The one failed call, E5D-034, returned empty DeepSeek JSON-output content. One exact same-request/configuration transport retry succeeded. The first-pass failure remains preserved for audit.

Post-hoc development analysis recorded:

- E5D-017 — retrieved-condition Layer C completeness miss;
- E5D-030 — Layer B candidate-generation/retrieval miss;
- E5D-045 — Layer B near-boundary reference-page ranking miss, with a usable retrieved-condition answer;
- E5D-056 — retrieved-condition answer-state/abstention miss;
- E5D-027 and E5D-034 — non-unique discovery wording / benchmark ambiguity.

Preliminary ambiguity-adjusted end-to-end development correctness remains 55/58 = 94.8%. This is a post-hoc analysis statistic, not a replacement frozen-benchmark score.

## Oracle/reference-evidence result

The oracle development run kept the exact same provider/model/prompt/reasoning/schema configuration. Only evidence source changed for answerable questions. Negative/abstention questions retained the original evidence as a negative control.

Run ID:

```text
deepseek-v4-pro-high-oracle-60
```

Results:

```text
selected questions: 60
hosted successes: 60
hosted failures: 0
request success rate: 1.0
answerability/status accuracy: 1.0
reference-page citation hit rate: 1.0
target-AD citation hit rate: 1.0
```

Recorded oracle evidence-pack SHA-256:

```text
33beaf3b0f6b45be80cf2ef70fc9ac94e1fe593986915c180c3685f494939b32
```

Recorded oracle response SHA-256:

```text
c1757226df9d7793bdce47bba4dd9b68517951d361720c768b58d1665784be75
```

Key interpretation:

- E5D-030 becomes correct with reference evidence, confirming the primary failure is Layer B retrieval.
- E5D-045 returns the complete publication names and dates with its reference page, confirming the source-page ranking limitation.
- E5D-017 becomes complete with isolated reference evidence, showing the original miss was evidence-conditioned Layer C completeness rather than inability to interpret the source statement.
- E5D-056 returns the correct `insufficient_evidence` state in the negative-control oracle run even though its evidence was not intentionally improved. This is documented as observable run-to-run hosted-model variability, not as an oracle-evidence gain.
- E5D-027/E5D-034 remain benchmark-ambiguity findings. Target-scoped oracle evidence cannot prove corpus-wide uniqueness.

The assistant semantic audit of the oracle review packet found no clear answer/reference contradiction. This is not labelled human review; the formal human rubric remains a separate artifact.

## Freeze tooling

Builder:

```text
full_corpus_pipeline/layer_c/build_hosted_qa_freeze.py
```

Validator:

```text
full_corpus_pipeline/layer_c/validate_hosted_qa_freeze.py
```

Regression tests:

```text
full_corpus_pipeline/tests/test_layer_c_hosted_qa_freeze.py
```

The builder binds the freeze to hashes of the development benchmark, retrieval freeze, retrieved/oracle evidence packs, audited run summaries, prompt/runner, response schema, provider adapter, evidence builders/runners, and evaluator.

It also verifies the audited development evidence:

```text
retrieved first pass: 59/60
exact transport retry: 1/1
oracle condition: 60/60
```

## Freeze commands

After pulling the repository, run:

```bash
.venv/bin/python -m unittest \
  full_corpus_pipeline.tests.test_layer_c_hosted_qa_freeze \
  -v
```

Build the freeze:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.build_hosted_qa_freeze
```

Validate it independently:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.validate_hosted_qa_freeze
```

Expected output artifact:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/hosted_qa_freeze.json
```

Commit that generated freeze before accessing any final benchmark material.

## Final-test gate

Only after `hosted_qa_freeze.json` is generated, validated, and committed:

1. open/finalize the sealed 40-question final benchmark;
2. human-review the final questions/reference evidence;
3. freeze final benchmark hashes;
4. run the one-time end-to-end final evaluation with frozen E5-D + frozen Layer C;
5. run the final oracle-reference-evidence diagnostic with the same Layer C settings; and
6. perform the reserved unseen-document ingestion/QA evaluation.

No provider/model/prompt/reasoning/evidence/citation/abstention settings may be changed in response to final-test outcomes.
