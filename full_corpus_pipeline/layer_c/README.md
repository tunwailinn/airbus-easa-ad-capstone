# Layer C — Hosted Evidence-Grounded QA

Layer C is the active answer-generation layer. Unlike frozen Layer A/B experiment code, active Layer C implementation lives directly in this folder.

## Files

- `config.py` — loads project-root `.env` without overriding explicit shell variables
- `providers/deepseek.py` — direct DeepSeek V4 Pro provider
- `hosted_qa_contract.schema.json` — machine-readable answer/abstention contract
- `hosted_gateway.py` — legacy/optional provider-neutral gateway
- `hosted_qa.py` — evidence-grounded prompt, output validation, and local citation resolution
- `build_evidence_packs.py` — deterministic frozen-E5-D top-5 evidence-pack builder
- `run_development.py` — development-only DeepSeek hosted QA batch runner
- `evaluate_development.py` — offline development evaluator + human semantic-review packet

## Boundary

```text
Question
→ frozen Layer B / E5-D
→ top-5 original-PDF evidence
→ Layer C DeepSeek V4 Pro QA
→ cited answer | insufficient evidence | conflicting evidence
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

## Canonical commands

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

Evaluate that run offline against the private human-reviewed development references:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.evaluate_development \
  --run-dir data_processed/evaluations/e5/layer_c/development/runs/deepseek-v4-pro-high-smoke
```

This writes an `evaluation/` subdirectory containing:

- `automatic_evaluation.json` — transport/status/citation/retrieval-support checks;
- `human_review.csv` — blank human semantic-review rubric; and
- `review_packet.md` — question, private reference answer, hosted answer, and citations side by side.

Private reference fields are joined only after inference and are never included in the model prompt. Semantic answer correctness and material-condition completeness remain human-reviewed rather than asking the evaluated model to grade itself.

The old root module names remain as thin compatibility entry points so earlier commands and tests continue to work.

## Current gate

DeepSeek V4 Pro is the declared development provider/model, but hosted-QA settings are not frozen yet. Do not create the hosted-QA freeze or open the sealed 40-question final benchmark until the development run, evaluation, and oracle-evidence comparison are complete.
