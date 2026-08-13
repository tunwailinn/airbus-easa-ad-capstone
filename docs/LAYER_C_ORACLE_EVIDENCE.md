# Layer C Oracle / Reference-Evidence Development Condition

## Purpose

This controlled development experiment estimates the Layer C generation/reasoning ceiling when the intended source evidence is supplied directly, without changing the hosted model or prompt.

It is used to separate:

- **Layer B retrieval/evidence-selection limitations** — the retrieved top 5 does not contain the source evidence needed for the human-reviewed answer; from
- **Layer C generation/reasoning/answer-state limitations** — the intended source evidence is supplied but the hosted answer remains wrong, incomplete, unsupported, or uses the wrong response status.

The final 40-question benchmark remains sealed during this experiment.

## Fixed generation configuration

The oracle condition keeps exactly the declared retrieved-evidence development configuration:

```text
provider: DeepSeek official API
provider adapter: deepseek-direct-v1.1
model: deepseek-v4-pro
thinking: enabled
reasoning_effort: high
max_tokens: 4096
temperature: not used in thinking mode
prompt: e5-hosted-qa-prompt-v1.0-dev
response contract: e5-hosted-qa-contract-v1.0
hosted runner: e5-hosted-qa-runner-v1.1
```

The oracle runner rejects a reasoning effort other than `high` and a max-token value other than `4096` so the evidence source is the only intended experimental change.

## What changes

Retrieved-evidence development condition:

```text
question
→ frozen E5-D top-5 evidence
→ DeepSeek V4 Pro
```

Oracle/reference-evidence condition:

```text
question
→ source chunks from the human-reviewed target AD and reference pages/sections
→ same DeepSeek V4 Pro configuration
```

No retrieval is run or retuned in the oracle condition.

## No answer leakage

The oracle builder does **not** put the gold/reference answer into the model prompt.

The hosted prompt contains only:

```text
question_id
question
evidence
```

The following private benchmark fields are used only offline for evidence selection/evaluation and are not rendered into the prompt:

- category;
- query mode;
- answerability label;
- target AD label;
- reference-page label;
- reference-section label;
- reference answer;
- required conditions;
- required exceptions; and
- retrieval relevance labels.

Reference pages and sections identify where the human-reviewed supporting source evidence is located. They are used to select original-PDF-derived frozen chunks, not to synthesize an answer.

## Answerable-question oracle evidence

For each answerable development question, the builder:

1. reads the private `target_ad_number`;
2. reads the human-reviewed `reference_pages`;
3. finds frozen E4 chunks whose `ad_number` equals the target AD and whose page range overlaps a reference page;
4. prioritizes chunks whose section matches a human-reviewed `reference_sections` entry;
5. guarantees reference-page coverage before filling remaining slots;
6. emits at most five source chunks with stable `EV1...EV5` IDs; and
7. fails rather than silently mixing multiple physical source PDFs when the target source cannot be resolved deterministically.

The source text still comes from the frozen original-PDF Layer B chunk store.

## Abstention / negative-control questions

The six `insufficient_conflict_abstention` questions intentionally have no answer-bearing reference page: the benchmark asks for details that the AD itself does not provide.

Creating an artificial positive oracle passage for those questions would invalidate the abstention task. Therefore their original frozen top-5 evidence is retained unchanged as a negative control.

This lets the oracle experiment test whether Layer C correctly recognizes that the requested detail is absent while improving evidence only for answerable questions.

## Reproducibility and immutability

Canonical builder:

```text
full_corpus_pipeline/layer_c/build_oracle_evidence_packs.py
```

Oracle evidence-pack version:

```text
e5-oracle-evidence-pack-v1.0
```

Default output:

```text
data_processed/evaluations/e5/layer_c/development/oracle_evidence_packs.jsonl
```

The builder writes a companion manifest containing SHA-256 hashes of:

- the frozen development questions;
- retrieval freeze;
- frozen E4 chunk store;
- frozen E5-D development report;
- retrieved-evidence packs; and
- generated oracle evidence packs.

The manifest also records the count of answerable reference-page oracle questions and negative controls.

## Commands

Pull the implementation and run the oracle evidence regression test:

```bash
git pull

.venv/bin/python -m unittest \
  full_corpus_pipeline.tests.test_layer_c_oracle_evidence \
  -v
```

Build the oracle evidence packs:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.build_oracle_evidence_packs
```

Inspect the generated manifest before inference:

```bash
cat data_processed/evaluations/e5/layer_c/development/oracle_evidence_packs.manifest.json
```

Run all 60 development questions under the oracle condition:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.run_oracle_development \
  --model deepseek-v4-pro \
  --reasoning-effort high \
  --max-tokens 4096 \
  --run-id deepseek-v4-pro-high-oracle-60
```

Evaluate the run offline:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.evaluate_development \
  --run-dir data_processed/evaluations/e5/layer_c/development/oracle_runs/deepseek-v4-pro-high-oracle-60
```

## Interpretation

For an answerable question:

- retrieved evidence wrong/missing, oracle answer correct → **retrieval/evidence-selection limitation**;
- retrieved answer wrong, oracle answer still wrong → **Layer C generation/reasoning limitation**;
- retrieved answer correct, oracle answer correct → **end-to-end success**;
- retrieved answer correct, oracle answer worse → investigate source-selection completeness and model variance before drawing conclusions.

For an abstention question, the evidence is intentionally unchanged. A wrong answer state under both conditions is a Layer C abstention/decision issue rather than a retrieval issue.

The oracle condition is a development diagnostic, not a production configuration and not a replacement benchmark score.

## Known development cases to inspect

The comparison is especially informative for the already documented cases:

- `E5D-017` — retrieved evidence present but applicability population was incompletely generated; expected to reveal whether the reference-page oracle evidence fixes completeness;
- `E5D-030` — frozen top-5 retrieval missed the target evidence; oracle should isolate this as a retrieval-caused answer error if the hosted answer becomes correct;
- `E5D-045` — reference page was outside frozen top 5 but the retrieved answer remained usable; oracle checks whether the complete publication details are recovered;
- `E5D-056` — negative-control evidence remains unchanged; if `status=answered` persists, that confirms a Layer C abstention-state limitation;
- `E5D-027` and `E5D-034` — the original discovery questions remain frozen and documented as corpus-wide ambiguous; oracle target evidence removes lifecycle distractors only for diagnostic comparison and does not retroactively repair the benchmark.

## Gate after oracle evaluation

After the oracle run is human-reviewed:

1. compare retrieved-evidence and oracle-evidence results question by question;
2. finalize retrieval-vs-generation error attribution;
3. decide whether the current DeepSeek/prompt/reasoning configuration is adequate without post-hoc overfitting;
4. write and validate `hosted_qa_freeze.json`; and
5. only then open the sealed 40-question final benchmark for the one-time final evaluation.
