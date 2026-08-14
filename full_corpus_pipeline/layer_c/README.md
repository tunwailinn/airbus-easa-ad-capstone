# Layer C — Hosted Evidence-Grounded QA

Layer C is the hosted answer-generation layer. Extraction/index construction remain local and deterministic; Layer C receives only a question plus evidence passages with stable IDs and returns a structured evidence-grounded answer or abstention.

## Current status

**FINAL EVALUATION COMPLETE / FROZEN.**

Completed:

- retrieved-evidence development QA;
- development oracle/reference-evidence diagnostic;
- hosted-QA freeze;
- human-reviewed 40-question final benchmark lock;
- one-time primary final run;
- offline automatic evaluation;
- human semantic review;
- final oracle/reference-evidence diagnostic;
- one exact audited transport retry for oracle `E5F-035`.

Authoritative final semantic result: **38/40 = 95.0%**.

The next project phase is the five frozen unseen-PDF temporary-QA and permanent-ingestion evaluation. Do not retune Layer C from final-test or unseen-test observations.

## Main files

Core QA:

- `config.py` — project-root `.env` loading;
- `providers/deepseek.py` — direct DeepSeek V4 Pro provider;
- `hosted_qa_contract.schema.json` — machine-readable answer/abstention contract;
- `hosted_gateway.py` — optional provider-neutral gateway;
- `hosted_qa.py` — prompt construction, output validation, and local citation resolution.

Development:

- `build_evidence_packs.py` — frozen E5-D top-5 development evidence packs;
- `run_development.py` — retrieved-evidence development runner;
- `evaluate_development.py` — offline development evaluator;
- `build_oracle_evidence_packs.py` — development oracle/reference-evidence packs;
- `run_oracle_development.py` — development oracle runner.

Freeze/final benchmark:

- `build_hosted_qa_freeze.py`;
- `validate_hosted_qa_freeze.py`;
- `run_final_benchmark.py`;
- `run_locked_final_benchmark.py`;
- `evaluate_final.py`;
- `validate_final_benchmark_lock.py`.

Final oracle diagnostic:

- `build_final_oracle_evidence_packs.py`;
- `run_final_oracle.py`;
- `evaluate_final_oracle.py`;
- `retry_final_oracle_transport.py`.

## Architecture boundary

Primary final condition:

```text
Question
→ frozen Layer B / E5-D retrieval
→ top-5 original-PDF evidence
→ frozen Layer C DeepSeek V4 Pro QA
→ cited answer | insufficient_evidence | conflicting_evidence
→ offline automatic + human semantic evaluation
```

Oracle diagnostic condition:

```text
Question
→ human-reviewed target AD/reference pages selected offline
→ source chunks from those pages
→ exact same frozen Layer C DeepSeek configuration
→ diagnostic comparison against primary
```

For the four abstention/negative-control questions, the oracle condition deliberately keeps the exact primary evidence rather than manufacturing answer-bearing evidence.

Layer C must not run or retune retrieval.

## Frozen generation configuration

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

The hosted prompt contains only the question and supplied evidence. Private benchmark fields such as reference answers, target AD labels, reference pages, category/query mode, answerability, and scoring labels are not sent to the model.

## Credentials

Create the local secrets file once:

```bash
cp .env.example .env
```

Then add:

```dotenv
DEEPSEEK_API_KEY=your-real-api-key
```

`.env` and `.env.*` are gitignored; `.env.example` is versioned. Explicit shell environment variables override `.env` values.

Install/update dependencies after pulling changes:

```bash
.venv/bin/python -m pip install -r requirements-v3.txt
```

## Development commands — preserved for reproducibility

Retrieved evidence:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.build_evidence_packs

.venv/bin/python -m full_corpus_pipeline.layer_c.run_development \
  --model deepseek-v4-pro \
  --reasoning-effort high \
  --max-tokens 4096 \
  --run-id <run-id>

.venv/bin/python -m full_corpus_pipeline.layer_c.evaluate_development \
  --run-dir data_processed/evaluations/e5/layer_c/development/runs/<run-id>
```

Development oracle:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.build_oracle_evidence_packs

.venv/bin/python -m full_corpus_pipeline.layer_c.run_oracle_development \
  --model deepseek-v4-pro \
  --reasoning-effort high \
  --max-tokens 4096 \
  --run-id <oracle-run-id>
```

## Final benchmark commands — audit/reproduction only

The primary final benchmark has already been run. **Do not run it again as a new primary experiment.** The commands below document the completed workflow.

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.validate_final_benchmark_lock
.venv/bin/python -m full_corpus_pipeline.layer_c.run_locked_final_benchmark
.venv/bin/python -m full_corpus_pipeline.layer_c.evaluate_final
```

Primary final result:

- 40/40 hosted requests successful;
- retrieval Recall@5: **35/36 = 97.22%**;
- known-document Recall@5: **24/24 = 100%**;
- discovery Recall@5: **11/12 = 91.67%**;
- human semantic accuracy: **38/40 = 95.0%**.

## Final oracle commands — audit/reproduction only

The oracle diagnostic has already been completed. The commands document the workflow:

```bash
.venv/bin/python -m unittest \
  full_corpus_pipeline.tests.test_layer_c_final_oracle \
  -v

.venv/bin/python -m full_corpus_pipeline.layer_c.build_final_oracle_evidence_packs
.venv/bin/python -m full_corpus_pipeline.layer_c.run_final_oracle
.venv/bin/python -m full_corpus_pipeline.layer_c.evaluate_final_oracle
```

Original oracle batch:

- selected: 40;
- successes: 39;
- technical/provider failures: 1 (`E5F-035`);
- reference-page citation hit rate: 100%;
- target-AD citation hit rate: 100%.

One exact transport retry was then performed:

```bash
.venv/bin/python -m full_corpus_pipeline.layer_c.retry_final_oracle_transport \
  --question-id E5F-035
```

The retry recovered successfully while preserving prompt payload hash, question, evidence, model, prompt, reasoning mode, and max-token limit. The original oracle failure remains preserved in the first-run audit trail.

## Final attribution summary

- `E5F-021`: **Layer B retrieval/candidate-generation failure confirmed** — primary wrong, oracle correct.
- `E5F-011`: **Layer C evidence-selection/completeness sensitivity** — relevant evidence was available in primary; focused oracle evidence makes the same model answer correctly.
- `E5F-040`: **Layer C status-calibration/run-to-run variability** — unchanged negative-control evidence produced `insufficient_evidence` in primary and `answered` in oracle, while the prose remained appropriately cautious.
- `E5F-035`: **technical/provider failure only** in the original oracle batch; exact retry recovered.

## Reporting rule

Never replace the strict final score with an oracle or retry-adjusted value.

Use:

```text
Primary final end-to-end semantic accuracy: 38/40 = 95.0%
```

Oracle and transport-retry outputs exist only for diagnosis and audit.

## Next gate

Proceed to the five frozen unseen PDFs under:

```text
evaluation_sets/unseen_incoming_5_v1/
```

Evaluate temporary uploaded-PDF QA first, then permanent ingestion without retraining. Keep unseen results separate from the 40-question final benchmark.