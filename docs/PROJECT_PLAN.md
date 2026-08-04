# Project Plan v3.1

The authoritative detailed plan is
[`../airbus_easa_ad_project_exact_plan.md`](../airbus_easa_ad_project_exact_plan.md).

## Target outcome

By 30 September 2026, deliver a two-layer assistant over all 1,809 frozen Airbus
EASA AD PDF records:

1. a section-complete content catalogue for filtering and browsing; and
2. page-aware RAG over original PDFs for complex compliance interpretation.

The project does not claim fully normalized compliance logic across 1,809 ADs.

## Fixed design

- Immutable audit source: `gold_releases/easa_airbus_ad_gold_v2/`.
- Active content gold: 50 records, split 30 development / 20 locked test.
- Development corpus: 1,804 PDFs after five unseen PDFs are excluded.
- Final corpus: 1,809 records after permanent-ingestion testing.
- Extraction formats: individual content JSON and combined JSONL.
- Extraction method: deterministic local parser; zero hosted extraction calls.
- Retrieval source: original PDF page text, never generated JSON alone.
- QA benchmark: 50 locked questions, including complex compliance cases.
- No standalone classification or reference-summary benchmark.

## Work packages

| Dates | Work | Gate |
|---|---|---|
| 4–9 Aug | Approve v3.1; validate content projection and QA v2 | Frozen active evaluation artifacts |
| 4 Aug | Run local pilot and extract 1,804 development records | Completed schema-valid JSON/JSONL |
| 10–16 Aug | Review parser field/section quality | Frozen parser and error analysis |
| 17–23 Aug | Prepare original-PDF page-aware inputs | Retrieval-ready page text |
| 24–30 Aug | Chunk original PDFs and build E0/E4 indexes | Page-aware BM25/FAISS indexes |
| 31 Aug–6 Sep | Evaluate retrieval | Recall/MRR/nDCG results |
| 7–13 Sep | Evaluate retrieval-time compliance QA | Correctness/citation/abstention results |
| 14–20 Sep | Test permanent ingestion | Five ingestions; final count 1,809 |
| 21–27 Sep | UI, errors, thesis, reproducibility | Reviewable final system |
| 28–30 Sep | Final checks and demonstration | Final package |

## Completion gates

### Content extraction

- Structure reliable identity/publication, model, identifier, and lifecycle
  wording fields.
- Preserve raw Applicability, Definitions, Reason, complete
  Requirements/Compliance, publication-reference, and Remarks sections.
- Do not machine-normalize compliance conditions, exceptions, repeats,
  follow-on/terminating actions, unsafe-condition decomposition, or credit logic.
- Schema validity target ≥0.98; deterministic metadata macro F1 target ≥0.80.
- Raw action wording is graded for section boundaries/source containment rather
  than equivalence to manually structured action units.

### Original-PDF RAG

- Chunks come from original page text and never mix PDFs.
- E0 uses flat dense-only retrieval.
- E4 uses section-aware BM25+dense retrieval, RRF, reranking, and lifecycle
  filtering.
- The answer generator preserves all material source conditions and cites the
  relevant page or abstains.

### Ingestion

- Temporary upload is isolated and removable.
- Permanent ingestion requires explicit confirmation.
- Exact duplicates are rejected.
- Ambiguous lifecycle state cannot replace operational selection.
- No training occurs during upload or ingestion.

## Immediate next action

Obtain supervisor approval of v3.1, human spot-check the content 50 and QA v2
references, review the completed local extraction, then build page-aware E0/E4
indexes.
