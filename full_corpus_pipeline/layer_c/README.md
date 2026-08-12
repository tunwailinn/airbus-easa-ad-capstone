# Layer C — Hosted Evidence-Grounded QA

Layer C is the active answer-generation layer. Unlike frozen Layer A/B experiment code, active Layer C implementation lives directly in this folder.

## Files

- `hosted_qa_contract.schema.json` — machine-readable answer/abstention contract
- `hosted_gateway.py` — provider-neutral hosted-model gateway
- `hosted_qa.py` — evidence-grounded prompt, output validation, and local citation resolution
- `build_evidence_packs.py` — deterministic frozen-E5-D top-5 evidence-pack builder
- `run_development.py` — development-only hosted QA batch runner

## Boundary

```text
Question
→ frozen Layer B / E5-D
→ top-5 original-PDF evidence
→ Layer C hosted QA
→ cited answer | insufficient evidence | conflicting evidence
```

Layer C must not run or retune retrieval.

## Canonical commands

Build development evidence packs:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.build_evidence_packs
```

Run a development smoke test:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.run_development \
  --model <development-model-name> \
  --limit 3 \
  --run-id <model>-smoke
```

Run one prepared evidence pack:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.hosted_qa \
  --evidence-pack path/to/evidence_pack.json \
  --model <development-model-name>
```

The old root module names remain as thin compatibility entry points so earlier commands and tests continue to work.

## Current gate

Provider/model/prompt/reasoning settings are still development-only. Do not create the hosted-QA freeze or open the sealed 40-question final benchmark until one Layer C configuration has been selected from development results.
