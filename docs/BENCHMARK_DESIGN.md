# Benchmark Design v3.1

## Evaluation principle

The two layers are evaluated separately:

- the content 20-record test set measures reliable structured fields and raw
  section preservation; and
- the 50-question QA v2 benchmark measures retrieval and interpretation from
  original PDF passages.

Complex compliance questions are not expected to be answerable from the
structured fields alone.

## Content extraction reference

Immutable audit source:

```text
gold_releases/easa_airbus_ad_gold_v2/
```

Active derived dataset:

```text
evaluation_sets/easa_airbus_ad_content_gold_50_v2/
```

The derived records retain identity/publication metadata, applicability,
definitions, Reason content, action text, publication identifiers, supersedure,
and reviewed AMOC/contact remarks. Live local extraction preserves complete raw
standard sections while excluding machine-normalized compliance semantics and
all evidence/review/system metadata.

### Split

- 30 development records.
- 20 locked test records.
- Grouping key: `base_ad_number`.
- Seed: 42.

### Extraction metrics

- Schema validity.
- Field precision, recall, and macro F1.
- Normalized exact match.
- Coverage and failure rate.
- Raw-section boundary and source-text containment accuracy.
- Local runtime and latency; hosted extraction tokens/cost are zero.

Exact-match scores for `required_actions` are secondary because the local
parser preserves the full printed compliance section while the human reference
may contain multiple structured or paraphrased action units. The primary
deterministic-extraction assessment separates header metadata accuracy from raw
section-boundary accuracy.

## QA benchmark v2

```text
evaluation_sets/easa_airbus_ad_qa_50_v2/
```

| Category | Count | Primary layer tested |
|---|---:|---|
| Identity and snapshot lifecycle | 8 | Metadata + retrieval |
| Applicability | 8 | Original applicability passages |
| Required action and compliance | 16 | Original compliance passages |
| Referenced publication | 6 | Metadata + source verification |
| Conditional or multi-passage | 6 | Multi-passage PDF RAG |
| Insufficient/conflict/abstention | 6 | Answer safeguards |
| **Total** | **50** | |

The immutable audit annotations may be used privately to construct reference
answers and source pages. The live QA system must retrieve original PDF chunks;
it may not use hidden gold annotations or treat structured JSON fields as final
compliance evidence.

### QA grading

Measure:

- correct AD and page retrieval;
- answer correctness;
- preservation of conditions, alternatives, intervals, and terminating effects;
- page-citation correctness;
- abstention accuracy; and
- unsupported-claim rate.

## Retrieval experiment

- **E0:** flat chunks with dense-only retrieval.
- **E4:** section-aware original-PDF chunks, BM25, local embeddings, FAISS, RRF,
  metadata/lifecycle filtering, and reranking.

Measure Recall@1/3/5, MRR, nDCG@5, and correct-source/page retrieval.

## Unseen evaluation

Five non-gold PDFs from five distinct families remain frozen at
`evaluation_sets/unseen_incoming_5_v1/`. They are excluded from the 1,804-PDF
development corpus, tested temporarily, then permanently ingested to reach
1,809.

Test isolation, clearing, citations, duplicate rejection, index updates,
lifecycle safeguards, and absence of retraining.

## Locking rules

- Do not tune on the locked 20 or QA v2 questions.
- Do not use the five unseen PDFs during development.
- Version changed schemas and benchmarks instead of overwriting audit sources.
- Human spot-check QA wording/reference pages before final scoring.
- Report actual results, including failed and abstained cases.
