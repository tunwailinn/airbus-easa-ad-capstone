# Agent Guide: Airbus EASA AD Capstone v3.1

Read this file before changing code, data, experiments, or documentation.

## 1. Project identity

- Student: Tun Wai Lin
- Execution window: 13 July–30 September 2026
- Frozen corpus: 1,809 physical PDF records / 1,808 base AD families
- Scope: Airbus S.A.S. EASA ADs already present in the frozen snapshot
- Goal: section-complete local content extraction plus original-PDF RAG/QA

The prototype supports engineering review. It does not determine legal
compliance, authorize maintenance, or replace licensed judgment.

## 2. Authoritative methodology

`airbus_easa_ad_project_exact_plan.md` is the authoritative v3.1 plan.

The system has two layers:

```text
Section-complete content records
→ filtering, browsing, metadata lookup, raw difficult-section access

Original PDF page chunks + RAG
→ complex compliance timing, conditions, exceptions, branches, and QA
```

Do not claim that the 1,809 records contain fully normalized compliance logic.
The defensible contribution is the integrated section-complete extraction,
page-aware retrieval, retrieval-time interpretation, lifecycle, and ingestion
workflow.

## 3. Fixed scope

Included:

- final EU-issued Airbus S.A.S. EASA AD PDFs in the snapshot;
- structured reliable fields plus raw Applicability, Definitions, Reason,
  Requirements/Compliance, reference, and Remarks sections;
- original-PDF hybrid retrieval;
- page-cited corpus and temporary-document QA;
- confirmed permanent ingestion without retraining.

Excluded:

- PADs, SIBs, foreign-issued ADs, Airbus Helicopters, Airbus Canada, engines,
  and other approval holders;
- Service Bulletins as primary documents;
- missing historical revision acquisition;
- full-corpus normalized compliance extraction;
- standalone classification and reference-summary benchmarks;
- aircraft-specific compliance calculation or maintenance authorization.

## 4. Non-negotiable data rules

1. Treat raw/canonical PDFs as immutable.
2. Keep OCR as a derivative.
3. Use one manifest row and one content record per physical PDF.
4. Never merge requirements or passages from different PDF versions.
5. Keep lifecycle/latest selection outside content JSON.
6. Group evaluation splits by `base_ad_number`.
7. Keep gold references separate from predictions.
8. Keep parser/model version, prompt, cost, confidence, review, source, hash,
   path, and processing state in sidecars.
9. Detailed compliance answers must use retrieved original-PDF passages.
10. Answers cite AD number, source PDF, page, and section when available.
11. Preserve all material source conditions and abstain when support is
    incomplete or conflicting.

## 5. Immutable audit source

Preserve `gold_releases/easa_airbus_ad_gold_v2/` unchanged. It is used only for
reproducible projection and private evaluation-reference construction. It is
not the application dataset.

`docs/PDF_TO_GOLD_FRAMEWORK.md` remains authoritative for maintaining legacy
evidence-bearing releases. Frozen selections/queues remain read-only, automated
validation never grants human approval, and releases are never overwritten.

## 6. Active content contract

The active dataset is:

```text
evaluation_sets/easa_airbus_ad_content_gold_50_v2/
```

Permitted record sections:

- `ad_identity`;
- `publication`;
- raw `applicability` plus family/model tags;
- raw `definitions` and `reason` sections when printed;
- `required_actions` containing the complete raw compliance block;
- parsed `referenced_publications` plus complete raw reference text;
- revision, supersedure, correction, and cancellation wording; and
- raw `remarks`, including printed AMOC/contact content.

Do not add machine-normalized compliance limits, conditions, exceptions,
intervals, follow-on/terminating relationships, unsafe-condition decomposition,
previous-credit logic, evidence, or system metadata. Preserve those difficult
concepts inside their complete raw sections.

Raw action/applicability text may naturally contain time or condition wording.
It must not be treated as a complete normalized compliance model.

## 7. Fixed evaluation

- Active content gold: 50 records.
- Split: 30 development / 20 locked test, seed 42.
- QA benchmark: `evaluation_sets/easa_airbus_ad_qa_50_v2/`, 50 questions.
- Unseen set: five non-gold PDFs from five distinct families.
- Development corpus: 1,804 PDFs.
- Final corpus: 1,809 PDFs after ingestion testing.

Do not tune on the locked 20, QA v2, or unseen PDFs.

Primary comparison:

- E0: flat dense-only retrieval.
- E4: section-aware original-PDF BM25+dense retrieval, FAISS, RRF, reranking,
  metadata, and lifecycle filtering.

## 8. Working protocol

Authority order:

1. current user request;
2. this `AGENTS.md`;
3. `airbus_easa_ad_project_exact_plan.md`;
4. `docs/PROJECT_STATUS.md`;
5. `docs/DECISIONS.md`;
6. `docs/BENCHMARK_DESIGN.md`;
7. `docs/PROJECT_PLAN.md`;
8. `docs/PDF_TO_GOLD_FRAMEWORK.md` for legacy audit releases.

Before work:

1. Read `docs/PROJECT_STATUS.md`.
2. Inspect relevant inputs and outputs.
3. Distinguish implemented artifacts from unexecuted stages.
4. Preserve unrelated working-tree changes.

During work:

- use versioned schemas, prompts, datasets, benchmarks, and run directories;
- fail closed on invalid content;
- retain parser version and local latency in extraction sidecars, and retain
  model, prompt, tokens, and cost for optional QA-time LLM calls;
- run a 30-document local content pilot before a full parser revision;
- build retrieval from original page text, not structured records;
- require explicit confirmation before permanent ingestion; and
- never retrain during upload or ingestion.

After work:

1. Run validators/tests and record exact results.
2. Update `docs/PROJECT_STATUS.md`.
3. Add a dated methodological decision when appropriate.
4. Run Markdown and `git diff --check` checks.
5. Confirm immutable audit hashes remain unchanged.

## 9. Common commands

```bash
.venv/bin/python -m full_corpus_pipeline.validate_content_dataset \
  evaluation_sets/easa_airbus_ad_content_gold_50_v2 --expected-count 50

.venv/bin/python -m full_corpus_pipeline.validate_qa_benchmark

.venv/bin/python -m unittest discover -s full_corpus_pipeline/tests -v

.venv/bin/python -m full_corpus_pipeline.extract_corpus \
  --run-id local-content-development-1804-v2.1.3
```

Full-corpus and permanent-ingestion extraction are deterministic and local.
Hosted generation is optional only at QA answer time.

## 10. Immediate priority

1. Obtain supervisor approval for v3.1.
2. Human spot-check the content 50 and QA v2 references.
3. Review the completed 30-record local pilot and 1,804-record extraction.
4. Build original-PDF indexes and evaluate retrieval-time compliance QA.
5. Ingest the five held-out PDFs and verify the final count of 1,809.
