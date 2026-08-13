# Layer C Final Benchmark — One-Time Frozen Evaluation

## Status

The hosted-QA configuration is frozen in:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/hosted_qa_freeze.json
```

The final benchmark may now be opened exactly once for the primary frozen evaluation. No retrieval, prompt, model, reasoning-effort, evidence-depth, response-contract, or provider-adapter tuning is permitted after observing the final results.

The local sealed file remains:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/final_questions.jsonl
```

It contains 40 human-verified questions from the 16 final-test families. The file is intentionally not committed to the repository before the final run.

## Frozen primary configuration

```text
retrieval: E5-D
candidate generation: frozen E5-C top 20
reranker: Qwen/Qwen3-Reranker-0.6B @ e61197e
final evidence depth: 5
provider: DeepSeek official API
model: deepseek-v4-pro
thinking: enabled
reasoning_effort: high
max_tokens: 4096
prompt: e5-hosted-qa-prompt-v1.0-dev
response contract: e5-hosted-qa-contract-v1.0
semantic retry: prohibited
transport retry: exact same request/config only, separately audited
```

## One-time runner

Canonical command:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.run_final_benchmark
```

The runner validates the committed hosted-QA freeze **before reading the sealed final question file**. It then performs the complete primary sequence without an intermediate tuning/inspection gate:

```text
validate hosted-QA freeze
→ open/validate 40 final questions
→ frozen E5-C candidate generation
→ frozen E5-D reranking
→ assemble top-5 source evidence
→ frozen DeepSeek Layer C QA
→ preserve primary retrieval + QA artifacts
```

The model-visible payload contains only:

```text
question_id
question
evidence
```

Private fields such as target AD, reference pages, reference answer, category labels, answerability labels, and required conditions/exceptions are not sent to the hosted model.

## Immutability

Primary output directory:

```text
data_processed/evaluations/e5/layer_c/final/primary/
```

The runner refuses to overwrite or repeat a non-empty primary directory. Do not delete the directory to manufacture a second primary result.

Expected primary artifacts:

```text
primary/
├── run_manifest.json
├── retrieval_report.json
├── evidence_packs.jsonl
├── responses.jsonl
├── failures.jsonl
└── run_summary.json
```

If a hosted request fails for a pure provider/transport reason, preserve the original primary failure. Do not rerun all 40 and do not make a semantic/configuration change. A separately audited identical retry may be added later for only the failed request(s), while the first-pass primary result remains authoritative.

## Offline evaluation

Only after the primary hosted run completes, join the private final references offline:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.evaluate_final
```

This writes:

```text
primary/evaluation/
├── automatic_evaluation.json
├── human_review.csv
└── review_packet.md
```

Automatic checks include request success, answerability/status accuracy, final E5-D retrieval support, target-AD citation hit, and reference-page citation hit. Semantic answer correctness, condition completeness, timing completeness, exception completeness, citation support, and unsupported claims remain human-review dimensions.

## Reporting policy

Report the strict 40-question primary final result first and unchanged.

Any later findings such as ambiguous discovery wording, provider variability, retrieval-vs-generation attribution, or oracle-evidence analysis are **post-hoc diagnostics** and must not replace the strict final score.

No development prompt/model/retrieval changes may be made in response to final-test errors.

## Oracle evidence after the primary final result

A final oracle/reference-evidence condition may be run only after the primary final retrieval + QA result is preserved. It is diagnostic only and uses the exact same frozen Layer C configuration while replacing retrieved evidence with human reference evidence. Its purpose is error attribution, not score replacement or tuning.
