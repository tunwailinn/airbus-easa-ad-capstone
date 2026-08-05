# E5 Status

Last updated: 5 August 2026

## Current state

E0/E4 are closed/frozen historical experiments. E5 is the active improvement path and uses a fresh development/final benchmark.

Implemented in repository:

- `docs/E5_ENGINEERING_AWARE_RETRIEVAL.md` — E5 methodology;
- `full_corpus_pipeline/prepare_e5_benchmark_families.py` — deterministic 24-development/16-final family selector;
- `full_corpus_pipeline/prepare_e5_authoring_packets.py` — source-grounded development authoring packets;
- `full_corpus_pipeline/validate_e5_questions.py` — count/family/leakage validator;
- `full_corpus_pipeline/e5_query_router.py` — deterministic AD/SB/intent router;
- `full_corpus_pipeline/e5_retrieval.py` — runnable E5-A exact-document/discovery lexical retriever;
- `full_corpus_pipeline/hosted_qa.py` — provider-configurable evidence-grounded hosted QA with deterministic citation resolution;
- unit tests for query routing, exact-document retrieval, and hosted-QA citation validation.

## Predeclared development progression

- E5-A: deterministic document routing + within-document BM25 + section preference;
- E5-B: add multi-passage/adjacency evidence assembly;
- E5-C: add `Qwen/Qwen3-Embedding-0.6B` dense signal;
- E5-D: add `Qwen/Qwen3-Reranker-0.6B`; optional predeclared BGE reranker comparator if runtime permits.

Only the new 60-question E5 development set may select among these configurations. The 40-question E5 final set is opened once after retrieval and hosted-QA settings are frozen.

## Hosted QA

Default configured provider/model:

```text
base URL: https://api.deepseek.com
model: deepseek-v4-pro
API key env: DEEPSEEK_API_KEY
thinking: enabled
reasoning effort: high
JSON output: required
```

The client never persists reasoning content. The model returns evidence IDs only; source/page/section citations are resolved and validated by application code.

## Immediate local execution gate

Run in order:

```bash
git pull origin main

.venv/bin/python -m unittest discover \
  -s full_corpus_pipeline/tests -v

.venv/bin/python -m full_corpus_pipeline.prepare_e5_benchmark_families

.venv/bin/python -m full_corpus_pipeline.prepare_e5_authoring_packets \
  --split development
```

Expected generated artifacts:

```text
evaluation_sets/easa_airbus_ad_e5_benchmark_v1/
├── family_split.csv
├── split_lock.json
└── authoring_packets/
    └── development/
        └── <base-ad>.authoring.json
```

Do not generate `--split final_test` authoring packets while E5 retrieval/model/prompt tuning is active.

After the development packets are created, author and human-verify the 60 development questions, validate them with:

```bash
.venv/bin/python -m full_corpus_pipeline.validate_e5_questions \
  --split development
```

Then run E5-A/B/C/D development evaluation, freeze one configuration, and only then open the final-test authoring/evaluation workflow.
