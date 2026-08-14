# Frozen Five-PDF Unseen-Document Evaluation

## Status

This experiment begins **after** the frozen E5 retrieval configuration, hosted-QA configuration, one-time 40-question final benchmark, human semantic review, and final oracle diagnostic are complete.

The strict E5 primary final result remains authoritative:

- 40 final questions;
- 38 semantic passes / 2 semantic failures;
- strict end-to-end semantic accuracy: **95.0%**;
- E5-D final Recall@5: **35/36 = 97.22%**.

The five unseen PDFs are a separate post-final generalization experiment. Their outcomes must not be used to retune the frozen parser, E5 retrieval, prompt, DeepSeek model/settings, response contract, or evidence depth.

## Frozen unseen set

Locked source:

```text
evaluation_sets/unseen_incoming_5_v1/selection.csv
```

The five distinct held-out AD families are:

| Stratum | AD | Base family | Pages | Revision | Correction |
|---|---|---|---:|---:|---|
| corrected | 2008-0008 | 2008-0008 | 2 | 0 | yes |
| revised | 2011-0041R1 | 2011-0041 | 4 | 1 | no |
| supersedure | 2011-0142 | 2011-0142 | 3 | 0 | no |
| long_document | 2026-0084 | 2026-0084 | 10 | 0 | no |
| simple_original | 2007-0173 | 2007-0173 | 2 | 0 | no |

Total source pages: **21**.

These PDFs were excluded from development extraction, verified page-text indexing, E0/E4, E5 development, E5 final benchmark construction, and hosted-QA selection.

## Evaluation sequence

The order is locked:

```text
U0 source/selection validation
→ U1 non-destructive unseen preparation
→ U2 human-reviewed unseen QA authoring + lock
→ U3 temporary-document retrieval + frozen Layer C QA
→ U4 offline/human temporary-QA evaluation
→ U5 permanent ingestion into an isolated evaluation store/index
→ U6 duplicate/lifecycle/index-update safeguards
→ U7 post-ingestion QA/citation verification
→ U8 final unseen-generalization report
```

Do not permanently ingest a held-out PDF before its temporary-document QA result has been preserved.

## U0/U1 — non-destructive preparation

Implementation:

```text
full_corpus_pipeline/prepare_unseen_evaluation.py
```

This stage:

1. validates that `selection.csv` contains exactly five distinct families and the five predeclared strata;
2. validates selection metadata against the frozen corpus manifest;
3. validates the corpus-manifest SHA-256 against `selection_lock.json`;
4. resolves each original PDF;
5. verifies exact source SHA-256 and page count;
6. refuses native pages marked as needing OCR/review;
7. runs frozen parser `content-local-v2.1.6` without retraining;
8. verifies extracted AD identity;
9. creates section-aware temporary chunks;
10. writes source-grounded authoring packets.

It does **not**:

- call DeepSeek or any hosted model;
- write to `data_incoming/`;
- alter the frozen corpus manifest;
- alter any retrieval index;
- perform lifecycle promotion;
- permanently ingest a PDF.

Run:

```bash
.venv/bin/python -m unittest \
  full_corpus_pipeline.tests.test_prepare_unseen_evaluation \
  -v

.venv/bin/python -m full_corpus_pipeline.prepare_unseen_evaluation
```

The default `--pdf-root` recursively searches the project root. If the frozen PDFs live elsewhere, provide that source root explicitly:

```bash
.venv/bin/python -m full_corpus_pipeline.prepare_unseen_evaluation \
  --pdf-root /path/to/frozen/pdf/root
```

Expected outputs:

```text
data_processed/evaluations/unseen_5/preparation/
├── preparation_summary.json
├── preparation_manifest.json
└── authoring_packets/
    ├── 2008-0008__ddc6ce36fb4396b1.authoring.json
    ├── 2011-0041R1__87291fa34d4626d4.authoring.json
    ├── 2011-0142__2ccf37afa30beb24.authoring.json
    ├── 2026-0084__4aef51837278b16c.authoring.json
    └── 2007-0173__3ce5544043070665.authoring.json
```

## U2 — unseen QA authoring

Only after U1 passes should the source packets be opened for question authoring.

Planned unseen QA set: **15 questions, three per PDF**. This small set is a generalization probe, not another tuning benchmark.

Question-design rules:

- all questions are known-document/temporary-document questions because the user has uploaded or selected one PDF;
- questions must be answerable from that PDF unless explicitly authored as an abstention check;
- preserve exact applicability, timing, units, branches, exceptions, lifecycle relationships and publication identifiers;
- reference pages must contain the answer evidence;
- no question may be sent to the hosted model until the question/reference record has been human reviewed and locked;
- the authoring step may not change the system configuration.

Recommended coverage across the 15 questions:

- identity/lifecycle/revision/correction/supersedure;
- applicability;
- required action/compliance timing;
- conditional/multi-passage reasoning where the source supports it;
- referenced publications;
- at least one evidence-insufficiency check if naturally supported by the five sources.

## U3 — temporary-document QA

Temporary QA must be session-scoped and must not add the document to the permanent corpus.

The final answer generator remains the frozen Layer C configuration:

```text
provider: DeepSeek official API
model: deepseek-v4-pro
thinking: enabled
reasoning_effort: high
max_tokens: 4096
prompt: e5-hosted-qa-prompt-v1.0-dev
response contract: e5-hosted-qa-contract-v1.0
final evidence depth: <=5
```

For each temporary document, passage ranking is restricted to that uploaded PDF. Candidate passages are section-aware and reranked with the pinned E5-D Qwen reranker before the top evidence is supplied to Layer C. No corpus-wide discovery is required for this temporary-document condition.

Primary unseen temporary-QA metrics:

- source preparation success;
- frozen-parser success/schema validity;
- temporary retrieval reference-page Recall@5;
- human semantic answer accuracy;
- condition/timing/exception completeness;
- citation support correctness;
- unsupported-claim rate;
- abstention correctness where applicable;
- hosted request/transport failures.

## U5/U6 — permanent ingestion evaluation

Permanent ingestion is performed **only after temporary results are preserved**.

Use an unseen-evaluation store/index first; do not mutate any frozen E5 benchmark index. The existing ingestion workflow must be tested for:

- exact source SHA-256 duplicate rejection;
- frozen deterministic extraction;
- no model retraining;
- lifecycle decision and operational-selection behavior;
- revision/correction/supersedure safeguards;
- source provenance preservation;
- chunk/index append behavior in the evaluation index;
- repeat-ingestion rejection;
- post-ingestion QA citations.

The permanent ingestion implementation is:

```text
full_corpus_pipeline/permanent_ingest.py
```

The five held-out documents may eventually form part of the post-evaluation operational corpus, but frozen thesis benchmark indexes and their hashes remain immutable audit artifacts.

## Interpretation boundary

Report unseen outcomes separately from the E5 final score.

A failure may be attributed to:

- source/native-text preparation;
- deterministic extraction;
- temporary passage selection;
- Layer C generation/status behavior;
- permanent-ingestion duplicate handling;
- lifecycle handling;
- index update;
- post-ingestion retrieval/QA.

Do not silently fix the system based on a held-out failure and then report the fixed result as the original unseen score. Any later fix is a post-hoc engineering improvement and must be labelled separately.
