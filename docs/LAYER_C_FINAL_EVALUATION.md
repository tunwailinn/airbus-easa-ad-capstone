# Layer C Final Evaluation

## Status

The strict one-time E5 final benchmark has been completed with the frozen retrieval and hosted-QA configuration. The primary result is immutable. No retrieval, prompt, model, reasoning-effort, evidence-depth, response-contract, or provider-adapter tuning is permitted from final-test observations.

Final benchmark:

- 40 human-reviewed final questions;
- 36 answerable questions + 4 abstention/conflict questions;
- 24 known-document + 12 identifier-free discovery + 4 abstention/conflict;
- final questions SHA-256: `f6b008c1b5d24160cb5718e2d4e91a7e0d323277a531654e4b5c3a33995c9a85`.

## Strict primary automatic result

- hosted requests: **40/40 successful**;
- answerability/status accuracy: **1.0000**;
- frozen E5-D Recall@1: **0.8333**;
- frozen E5-D Recall@3: **0.9722**;
- frozen E5-D Recall@5: **0.9722 (35/36)**;
- MRR@5: **0.8981**;
- nDCG@5: **0.9173**;
- correct source@5: **0.9722**;
- correct source+page@5: **0.9722**;
- reference-page citation hit rate: **0.9722**;
- target-AD citation hit rate: **0.9722**.

Query-mode retrieval:

- known-document Recall@5: **1.0000 (24/24)**;
- discovery Recall@5: **0.9167 (11/12)**.

## Human semantic review — strict primary result

The human-approved primary semantic result is:

- semantic passes: **38/40**;
- semantic failures: **2/40**;
- strict end-to-end semantic accuracy: **95.0%**.

This **38/40 = 95.0%** value is the primary final semantic result and must not be replaced by any ambiguity-adjusted, oracle-evidence, or post-hoc score.

### E5F-011 — FAIL — Layer C completeness/relevance

The correct target AD/reference evidence was available in the frozen top-5. The hosted answer did not provide the approved applicability answer — `A300F4-605R` and `A300F4-622R`, all manufacturer serial numbers with Airbus modification 12046 embodied in production — and shifted instead to lower-deck cargo-door/frame-fork part-number details.

Primary attribution: **Layer C answer selection/completeness with relevant evidence available**.

### E5F-021 — FAIL — Layer B retrieval/candidate generation

The approved target is `2018-0289R1`, but the frozen retrieval condition did not contain the target reference evidence in its support and the hosted answer selected `2025-0111`.

Primary attribution: **Layer B retrieval/candidate-generation failure**.

### E5F-015 — PASS with post-hoc ambiguity note

The human-approved strict result is PASS. The evidence also contains superseded `2008-0101`, which originally imposed the same requirement, while target `2009-0075` superseded it and retained the requirement. The hosted answer identifies and explains both. Preserve this as a benchmark/lifecycle ambiguity note only; do not remove it from the strict denominator.

### E5F-030 — PASS with citation-page diagnostic

The answer correctly identifies the two referenced Airbus Service Bulletins. The canonical reference-page citation check missed the approved page. Preserve this as a citation-page diagnostic rather than an answer failure.

## Final oracle/reference-evidence diagnostic

The final oracle condition is post-hoc only and exists to improve error attribution. It must use the exact frozen Layer C provider/model/prompt/settings and change only the evidence source.

Implemented files:

```text
full_corpus_pipeline/layer_c/build_final_oracle_evidence_packs.py
full_corpus_pipeline/layer_c/run_final_oracle.py
full_corpus_pipeline/layer_c/evaluate_final_oracle.py
full_corpus_pipeline/tests/test_layer_c_final_oracle.py
```

Oracle evidence policy:

- 36 answerable questions: frozen E4 source chunks from the private target AD and human-reviewed reference pages, with reference sections used only for deterministic prioritization;
- 4 abstention/conflict questions: exact primary frozen top-5 prompt evidence retained as a negative control;
- maximum evidence depth: 5;
- no retrieval run or retuning;
- model-visible payload remains only `question_id`, `question`, and `evidence`;
- reference answers, target labels, answerability labels, category/query-mode labels and reference-page labels do not enter the prompt.

Generation configuration remains:

```text
provider: DeepSeek official API
model: deepseek-v4-pro
thinking: enabled
reasoning_effort: high
max_tokens: 4096
prompt: e5-hosted-qa-prompt-v1.0-dev
response contract: e5-hosted-qa-contract-v1.0
semantic retry: prohibited
```

### Commands

Run safeguards:

```bash
.venv/bin/python -m unittest \
  full_corpus_pipeline.tests.test_layer_c_final_oracle \
  -v
```

Build the final oracle packs:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.build_final_oracle_evidence_packs
```

Run the 40-question oracle diagnostic:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.run_final_oracle
```

Evaluate it offline:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.evaluate_final_oracle
```

Expected diagnostic outputs:

```text
data_processed/evaluations/e5/layer_c/final/oracle/
├── evidence_packs.jsonl
├── evidence_packs.manifest.json
└── run/
    ├── run_manifest.json
    ├── run_summary.json
    ├── responses.jsonl
    ├── failures.jsonl
    └── evaluation/
        ├── automatic_evaluation.json
        ├── human_review.csv
        └── review_packet.md
```

## Interpretation

The highest-value comparisons are:

- `E5F-021`: if correct under oracle evidence, this confirms the primary failure is Layer B retrieval/candidate generation;
- `E5F-011`: if still wrong under oracle evidence, this strengthens Layer C generation/reasoning attribution; if it becomes correct, the primary failure should be interpreted more narrowly as evidence-conditioned answer selection/completeness despite the target evidence technically being present;
- abstention questions: because their evidence is intentionally unchanged, any output change is model run-to-run variability rather than an oracle-evidence improvement.

Whatever the oracle result, **the strict primary final semantic score remains 38/40 = 95.0%**.

## Remaining project evaluation

After the oracle diagnostic is reviewed, the final major evaluation is the five frozen unseen-PDF ingestion + QA cases. Those cases remain separate from the 40-question final benchmark and must be reported as unseen-document generalization rather than used for tuning the primary final system.
