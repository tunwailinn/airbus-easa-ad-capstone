# Frozen Five-PDF Unseen-Document Evaluation

## Status

This experiment begins **after** the frozen E5 retrieval configuration, hosted-QA configuration, one-time 40-question final benchmark, human semantic review, and final oracle diagnostic are complete.

The strict E5 primary final result remains authoritative:

- 40 final questions;
- 38 semantic passes / 2 semantic failures;
- strict end-to-end semantic accuracy: **95.0%**;
- E5-D final Recall@5: **35/36 = 97.22%**.

The five unseen PDFs are a separate post-final generalization experiment. Their outcomes must not be used to retune the frozen parser, E5 retrieval, prompt, DeepSeek model/settings, response contract, or evidence depth.

### Current checkpoint — 17 August 2026

U0/U1 source validation and non-destructive preparation are **complete**.

Verified preparation result:

- preparation version: `unseen-5-preparation-v1.0`;
- status: `ready_for_human_question_authoring`;
- frozen documents: **5/5**;
- source SHA-256 matches: **5/5**;
- source pages: **21**;
- deterministic extraction successes: **5/5**;
- schema-valid extracted records: **5/5**;
- parser: `content-local-v2.1.6`;
- question inference started: **false**;
- permanent ingestion started: **false**.

Preparation bindings:

```text
selection.csv SHA-256:
f175477d68e2226b0793d742ad1ef0de99053b57e8334f1ca2c2962723e8c6a5

selection_lock.json SHA-256:
d2d12b393d544aff8f1c69dcff89a5305011b504f8ee54281dd40e20d725fd2c

corpus_manifest.parquet SHA-256:
00e7995de1ebfae1ebbc64fc447d7953567a3ef59854620bce0b606ac4f40a18

preparation_manifest.json SHA-256:
e3a60433348003b8e238a6704d40ddcd6e389e4f7804df92057f4eec9bbadc05
```

U2 question authoring has also been performed **as a draft only**. The draft contains **15 questions, exactly three per PDF**, but all 15 remain `needs_human_review` and therefore **must not be used for hosted inference yet**.

Draft question composition:

| Category | Count |
|---|---:|
| identity/lifecycle | 4 |
| applicability | 3 |
| required action/compliance | 3 |
| conditional/multi-passage | 3 |
| referenced publication | 1 |
| insufficient/conflict/abstention | 1 |
| **Total** | **15** |

Draft questions SHA-256:

```text
1d9600dd4379f501d0878adf6ae434076ef47ae0a299ef8be5bdc12cb55fc43b
```

Human-review state:

```text
human_verified: 0/15
needs_human_review: 15/15
```

The next gate is **human review and lock of the 15 unseen questions**. Do not start U3 temporary hosted QA or U5 permanent ingestion before that lock exists.

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
U0 source/selection validation                         COMPLETE
→ U1 non-destructive unseen preparation               COMPLETE
→ U2 human-reviewed unseen QA authoring + lock         IN PROGRESS — draft authored, review pending
→ U3 temporary-document retrieval + frozen Layer C QA  NOT STARTED
→ U4 offline/human temporary-QA evaluation             NOT STARTED
→ U5 permanent ingestion into isolated evaluation      NOT STARTED
→ U6 duplicate/lifecycle/index-update safeguards       NOT STARTED
→ U7 post-ingestion QA/citation verification           NOT STARTED
→ U8 final unseen-generalization report                NOT STARTED
```

Do not permanently ingest a held-out PDF before its temporary-document QA result has been preserved.

## U0/U1 — non-destructive preparation — COMPLETE

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

Preparation outputs:

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

## U2 — unseen QA authoring — HUMAN REVIEW PENDING

The draft unseen QA set contains **15 questions, three per PDF**. It is a generalization probe, not another tuning benchmark.

Question-design rules:

- all questions are known-document/temporary-document questions because one held-out PDF is explicitly selected;
- questions are answerable from that PDF unless explicitly authored as an abstention check;
- exact applicability, timing, units, branches, exceptions, lifecycle relationships and publication identifiers must be preserved;
- reference pages must contain the answer evidence;
- no question may be sent to the hosted model until the question/reference record has been human reviewed and locked;
- question review may correct the benchmark record, but may not change parser/retrieval/Layer-C configuration.

Draft coverage includes:

- correction/revision/supersedure and lifecycle interpretation;
- applicability and exclusion logic;
- required action/compliance timing;
- conditional/multi-passage reasoning;
- referenced publications;
- one evidence-insufficiency/abstention case.

Draft review artifacts are intentionally kept outside the permanent benchmark state until human approval. After review, create a locked unseen-question artifact and record its SHA-256 before inference.

## U3 — temporary-document QA — NOT STARTED

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

## U5/U6 — permanent ingestion evaluation — NOT STARTED

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
