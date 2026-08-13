# Layer C — Hosted Evidence-Grounded QA

Layer C is the active answer-generation layer. Unlike frozen Layer A/B experiment code, active Layer C implementation lives directly in this folder.

## Files

- `config.py` — loads project-root `.env` without overriding explicit shell variables
- `providers/deepseek.py` — direct DeepSeek V4 Pro provider
- `hosted_qa_contract.schema.json` — machine-readable answer/abstention contract
- `hosted_gateway.py` — legacy/optional provider-neutral gateway
- `hosted_qa.py` — evidence-grounded prompt, output validation, and local citation resolution
- `build_evidence_packs.py` — deterministic frozen-E5-D top-5 evidence-pack builder
- `run_development.py` — retrieved-evidence development DeepSeek batch runner
- `evaluate_development.py` — offline development evaluator + human semantic-review packet
- `build_oracle_evidence_packs.py` — development-only reference-page oracle evidence builder
- `run_oracle_development.py` — oracle/reference-evidence DeepSeek batch runner with generation settings locked to the retrieved-evidence condition

## Boundary

Retrieved-evidence condition:

```text
Question
→ frozen Layer B / E5-D
→ top-5 original-PDF evidence
→ Layer C DeepSeek V4 Pro QA
→ cited answer | insufficient evidence | conflicting evidence
→ offline development evaluation
```

Oracle/reference-evidence condition:

```text
Question
→ human-reviewed target AD + reference pages/sections (offline selection only)
→ source chunks from those pages; NO gold/reference answer in prompt
→ same Layer C DeepSeek V4 Pro QA configuration
→ offline development evaluation
```

Layer C must not run or retune retrieval.

## Local credentials

Create the local secrets file once:

```bash
cp .env.example .env
```

Then edit `.env` and replace the placeholder:

```dotenv
DEEPSEEK_API_KEY=your-real-api-key
```

`.env` and `.env.*` are gitignored; `.env.example` is the only dotenv template that is versioned. Existing process environment variables override values loaded from `.env`.

Install/update the project dependencies after pulling changes:

```bash
.venv/bin/python -m pip install -r requirements-v3.txt
```

## Retrieved-evidence development commands

Build development evidence packs:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.build_evidence_packs
```

Run the declared 3-question DeepSeek smoke test:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.run_development \
  --model deepseek-v4-pro \
  --reasoning-effort high \
  --max-tokens 4096 \
  --limit 3 \
  --run-id deepseek-v4-pro-high-smoke
```

Evaluate a run offline against the private human-reviewed development references:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.evaluate_development \
  --run-dir data_processed/evaluations/e5/layer_c/development/runs/deepseek-v4-pro-high-smoke
```

This writes an `evaluation/` subdirectory containing:

- `automatic_evaluation.json` — transport/status/citation/retrieval-support checks;
- `human_review.csv` — blank human semantic-review rubric; and
- `review_packet.md` — question, private reference answer, hosted answer, and citations side by side.

Private reference fields are joined only after inference and are never included in the model prompt. Semantic answer correctness and material-condition completeness remain human-reviewed rather than asking the evaluated model to grade itself.

## Oracle/reference-evidence development commands

Build the development oracle evidence packs:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.build_oracle_evidence_packs
```

For answerable questions, the oracle builder uses the benchmark's private target AD and human-reviewed reference pages to select source chunks. Reference sections only prioritize chunks on those pages. It never includes `reference_answer`, `required_conditions`, `required_exceptions`, category, query mode, answerability, or target labels in the hosted prompt.

For abstention/negative-control questions, there is intentionally no answer-bearing reference page. Their original frozen top-5 evidence is therefore retained so the oracle experiment does not manufacture evidence that the AD does not contain.

Run the oracle condition with the generation configuration locked to the retrieved-evidence development run:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.run_oracle_development \
  --model deepseek-v4-pro \
  --reasoning-effort high \
  --max-tokens 4096 \
  --run-id deepseek-v4-pro-high-oracle-60
```

The oracle runner rejects a reasoning effort other than `high` or a max-token value other than `4096`, preventing an accidental generation-setting change during the controlled comparison.

Evaluate the oracle run using the same offline evaluator:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.evaluate_development \
  --run-dir data_processed/evaluations/e5/layer_c/development/oracle_runs/deepseek-v4-pro-high-oracle-60
```

The comparison asks whether an error disappears when the intended source evidence is supplied. If it does, the failure is attributable to retrieval/evidence selection. If it persists with oracle evidence, it is attributable to Layer C generation/reasoning/answer-state behavior.

The old root module names remain as thin compatibility entry points so earlier commands and tests continue to work.

## Current gate

DeepSeek V4 Pro is the declared development provider/model, but hosted-QA settings are not frozen yet. Do not create the hosted-QA freeze or open the sealed 40-question final benchmark until the oracle-evidence run is complete, reviewed, and compared against the retrieved-evidence condition.
