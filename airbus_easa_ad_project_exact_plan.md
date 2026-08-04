# Airbus EASA AD Capstone — Exact Project Plan v3

**Student:** Tun Wai Lin

**Project:** Intelligent Engineering Document Automation for Aviation Maintenance

**Execution window:** 13 July–30 September 2026

**Plan version:** v3.1

**Methodology effective date:** 4 August 2026

## 1. Executive decision

The capstone will process the complete frozen snapshot of **1,809 physical PDF
records**, representing **1,808 base AD families**. The system will use a
deliberate two-layer architecture:

```text
Section-complete content records
→ filtering, browsing, exact metadata lookup, raw AD-section access,
  lifecycle selection

Original PDF page chunks + RAG
→ compliance timing, conditions, exceptions, branches, cross-references,
  repetitive intervals, terminating effects, and question answering
```

The 1,809-record extraction stage extracts all standard AD information sections.
Reliable metadata is structured, while difficult content—Definitions, Reason,
Required Action(s) and Compliance Time(s), publication-reference wording, and
Remarks—is preserved as raw text rather than semantically decomposed. The
original PDF passage remains authoritative for complex interpretation and page
citations.

This avoids turning wording such as:

> Within 500 flight cycles after the effective date, unless previously
> accomplished…

into several potentially distorted pre-computed fields. At question time, RAG
retrieves the relevant original paragraph and the LLM interprets the complete
wording while preserving its conditions and citations.

The project claim is therefore:

> A section-complete local extraction layer, with reliable fields structured
> and difficult fields preserved as raw text for retrieval-time interpretation.

It is not a claim that all 1,809 ADs contain fully normalized compliance logic.

## 2. Research objective and contribution

### 2.1 Objective

Build and evaluate a reproducible Airbus EASA AD assistant that:

1. creates a section-complete content catalogue of all 1,809 frozen PDF records;
2. uses local hybrid retrieval over original PDF page text;
3. interprets complex compliance questions from retrieved source passages;
4. provides source PDF and page citations;
5. supports temporary unseen-PDF QA and confirmed permanent ingestion; and
6. performs neither LLM nor embedding-model retraining during ingestion.

### 2.2 Defensible contribution

The integrated contribution is:

> Frozen-corpus governance + section-complete local AD extraction + separate
> lifecycle state + page-aware hybrid retrieval + retrieval-time compliance
> interpretation + temporary/permanent unseen-document ingestion + validated
> extraction and QA evaluation.

RAG, deterministic extraction, or aviation QA are not claimed as individually
novel.

### 2.3 Research questions

- **RQ1:** How accurately can a deterministic local parser extract reliable AD
  metadata and preserve complete raw difficult-section boundaries compared with
  the cleaned 20-record test set and PDF spot checks?
- **RQ2:** Does section-aware hybrid retrieval outperform flat dense-only
  retrieval for selecting the correct AD and original compliance passage?
- **RQ3:** Can an LLM correctly interpret conditions, timing, branches, and
  exceptions at question time from retrieved PDF text?
- **RQ4:** Can corpus and uploaded-PDF QA produce correct page-cited answers and
  reliable abstention?
- **RQ5:** Can unseen ADs be temporarily queried and permanently ingested
  without retraining or unsafe lifecycle replacement?

## 3. Fixed scope and corpus accounting

### 3.1 Included

- Final EU-issued EASA AD PDFs already present in the frozen Airbus S.A.S.
  snapshot.
- Original, revised, corrected, emergency-labelled, superseded, and
  cancellation-notice PDFs present in that snapshot.
- Section-complete content extraction: structured reliable fields plus raw
  difficult sections.
- Original-PDF page chunking and hybrid retrieval.
- Retrieval-time interpretation of compliance language.
- Corpus QA, temporary uploaded-PDF QA, and permanent ingestion.
- Source PDF, AD number, page, and section citations.
- Snapshot lifecycle filtering and ambiguity safeguards.

### 3.2 Excluded

- Proposed ADs, SIBs, foreign-issued ADs, Airbus Helicopters, Airbus Canada,
  engines, and other approval holders.
- Service Bulletins as primary indexed documents.
- Acquisition of missing historical revisions.
- Fully normalized compliance logic for all 1,809 records.
- Full-corpus manual evidence-span annotation.
- Standalone classification or reference-summary benchmarks.
- Aircraft-specific deadline calculation, legal-compliance determination,
  work-order generation, maintenance authorization, or release to service.

### 3.3 Exact counts

| Stage | Physical PDF records | Base AD families | Treatment |
|---|---:|---:|---|
| Frozen snapshot | 1,809 | 1,808 | Authoritative inventory |
| Unseen hold-out | 5 | 5 | Excluded from development extraction/indexes |
| Development corpus | 1,804 | Determined after exclusion | Extraction and development evaluation |
| Final corpus | 1,809 | 1,808 | After five permanent-ingestion tests |

The extraction target is 1,809 physical records, not 1,808 family summaries.
Versions are never merged into one content record.

## 4. Two-layer system architecture

### 4.1 Layer A — section-complete content catalogue

Purpose:

- exact AD lookup;
- filtering by date, ATA, aircraft family/model, or publication identifier;
- structured browsing in the UI;
- basic corpus analytics; and
- lifecycle-aware source selection using a separate sidecar.

This layer preserves difficult wording but does not claim normalized compliance
semantics. Detailed answers still verify the original PDF passage.

### 4.2 Layer B — original-PDF RAG

Purpose:

- retrieve complete applicability and compliance paragraphs;
- answer timing questions;
- preserve conditional and alternative branches;
- interpret `and`, `or`, `unless`, and `whichever occurs first/later`;
- connect definitions, exceptions, tables, follow-on actions, and terminating
  effects across passages; and
- cite the exact source PDF page.

The original PDF page text is authoritative when structured metadata and PDF
wording differ or when the structured record does not contain the needed detail.

### 4.3 Query flow

```text
Question
   ↓
Optional metadata filter from content catalogue
   ↓
BM25 + dense retrieval over original PDF chunks
   ↓
RRF + local reranking
   ↓
Retrieved source paragraphs/pages
   ↓
LLM interprets complete compliance logic
   ↓
Answer + AD/PDF/page/section citation or abstention
```

## 5. Data architecture and immutable boundaries

### 5.1 Immutable audit release

Preserve unchanged:

```text
gold_releases/easa_airbus_ad_gold_v2/
```

The evidence-bearing 50-record release proves prior validation. It is used only
to reproduce the content projection and privately construct extraction/QA
references. It is not used directly by the application or full-corpus
extraction pipeline.

No file in this release may be edited, deleted, or overwritten.

### 5.2 Active 50-record content evaluation dataset

```text
evaluation_sets/easa_airbus_ad_content_gold_50_v2/
├── records/
│   └── <ad-number>__<source-id>.json
├── records.jsonl
├── projection_manifest.parquet
├── projection_manifest.csv
├── projection_lineage.jsonl
├── projection_report.json
├── split_manifest.json
├── split_manifest.parquet
├── split_manifest.csv
├── split_lock.json
└── README.md
```

It is generated programmatically by
`full_corpus_pipeline/content_projection.py`. Manual cleanup is prohibited.

Earlier derived `content_gold_50_v1` and `lightweight_gold_50_v1` folders are
superseded experiment artifacts. They are not the immutable audit release.

### 5.3 Canonical full-corpus outputs

```text
data_processed/
├── extracted_records/
│   └── <ad-number>__<source-id>.json
├── extracted_ad_records_v1.jsonl
├── extraction_manifest.parquet
├── lifecycle_manifest.parquet
├── chunk_manifest.parquet
└── extraction_failures.csv
```

- Individual JSON and combined JSONL are authoritative for content records.
- Parquet is authoritative for operational manifests and analytics.
- CSV is a human-readable derivative only.
- Versioned run folders are never overwritten.

## 6. Section-complete content record contract

The active schema is
`full_corpus_pipeline/content_record.schema.json`, version 2.1.0.

### 6.1 Permitted structure

```json
{
  "ad_identity": {
    "ad_number": "2026-0123",
    "authority": "EASA",
    "document_type": "Airworthiness Directive",
    "revision": "R1",
    "correction_date": "2026-07-10",
    "design_approval_holder": "Airbus S.A.S."
  },
  "publication": {
    "subject": "Flight Controls",
    "issue_date": "2026-07-12",
    "effective_date": "2026-07-20",
    "effective_date_statement": "Revision 1: 20 July 2026; Original issue: ...",
    "ata_chapters": [{"code": "27", "title": "Flight Controls"}],
    "manufacturers": ["Airbus"],
    "type_model_designations": ["A320-214"],
    "tcds_numbers": ["EASA.A.064"]
  },
  "applicability": [
    {
      "text": "Exact applicability wording from the AD...",
      "aircraft_families": ["A320"],
      "models": ["A320-214"]
    }
  ],
  "definitions": {
    "text": "Complete printed Definitions section..."
  },
  "reason": {
    "text": "Complete printed Reason and unsafe-condition narrative..."
  },
  "required_actions": [
    {
      "action": "Complete printed Required Action(s) and Compliance Time(s) section, including paragraphs, tables, credit, exceptions, reporting, installation restrictions, and terminating-action wording..."
    }
  ],
  "referenced_publications": [
    {
      "type": "service_bulletin",
      "issuer": "Airbus",
      "number": "A320-XX-XXXX",
      "revision": "Revision 01",
      "date": "2026-06-01"
    }
  ],
  "referenced_publications_text": {
    "text": "Complete printed Ref. Publications section..."
  },
  "supersedure": {
    "statement": "This AD supersedes EASA AD 2024-0001.",
    "superseded_ad_numbers": ["2024-0001"]
  },
  "remarks": {
    "text": "Complete printed Remarks section, including AMOC and contact wording..."
  }
}
```

### 6.2 Explicitly excluded semantic structures

The content records preserve the printed wording but do not contain
machine-normalized:

- compliance limits or calculated deadlines;
- conditional logic;
- exceptions;
- repetitive intervals;
- grace periods;
- follow-on action relationships;
- terminating-action relationships;
- previous-action credit;
- unsafe-condition decomposition;
- part/serial-number logic objects;
- cross-paragraph relationship IDs.

Definitions, the Reason/unsafe-condition narrative, compliance conditions,
exceptions, previous-action credit, terminating-action wording, and AMOC/contact
remarks remain present inside raw sections. They are not converted into
separate machine-interpreted logic objects. RAG must retrieve the original PDF
paragraph before answering detailed compliance questions.

### 6.3 Sparse-record rules

1. Include only information stated in the current AD.
2. Omit absent values instead of emitting `null`, empty arrays, or placeholders.
3. Do not infer values from filenames, other versions, or external SBs.
4. Do not add evidence, confidence, review, status, machine, source, hash, path,
   or lifecycle fields.
5. Preserve exact identifiers, dates, paragraph labels, and high-level wording.
6. Do not reconstruct missing compliance relationships.
7. Invalid extraction becomes a sidecar failure, never a fabricated record.

## 7. Projection from the immutable 50

The projection retains:

- AD identity;
- publication metadata;
- raw applicability text plus family/model tags;
- definitions and Reason content available in the validated audit record;
- requirement action text plus printed paragraph label;
- referenced-publication identifiers; and
- supersedure statement/numbers; and
- reviewed AMOC/contact remark content.

It removes evidence spans, evidence IDs, assertions, annotations, benchmark and
classification fields, confidence, review state, source paths/hashes, machine
metadata, lifecycle state, and complex normalized compliance structures.

Every retained scalar maps to its original annotation section in
`projection_lineage.jsonl`. If a retained value cannot be projected without
loss or ambiguity, the build fails.

## 8. Evaluation design

### 8.1 Extraction split

The content 50 records retain the frozen family-level split with seed 42:

- 30 development records;
- 20 locked extraction-test records.

The locked 20 may not be used for prompt, model, retry, or threshold selection.

### 8.2 QA benchmark v2

Location:

```text
evaluation_sets/easa_airbus_ad_qa_50_v2/
```

| Category | Questions |
|---|---:|
| Identity and snapshot lifecycle | 8 |
| Applicability | 8 |
| Required action and compliance | 16 |
| Referenced publication | 6 |
| Conditional or multi-passage | 6 |
| Insufficient information, conflict, or abstention | 6 |
| **Total** | **50** |

The compliance and conditional questions are intentionally not answerable from
the structured fields alone. They test the PDF RAG layer. Their private
reference answers/pages may be derived from the immutable audit annotations,
but the live system must retrieve original PDF text.

### 8.3 Unseen incoming set

Five non-gold PDFs from five distinct families remain frozen at:

```text
evaluation_sets/unseen_incoming_5_v1/
```

They remain excluded from the 1,804-document development corpus and indexes
until temporary-upload evaluation. Permanent ingestion of the same five yields
the final 1,809-record corpus.

## 9. Section-complete full-corpus extraction

### 9.1 Flow

```text
PDF/page text
→ native text extraction
→ OCR only when necessary
→ deterministic local header and section parsing
→ content-schema validation
→ individual JSON + JSONL
→ operational manifests and failures
```

### 9.2 Local extraction contract

`full_corpus_pipeline/extract_corpus.py` runs locally and does not call a hosted
LLM. `full_corpus_pipeline/local_extractor.py` parses printed header values,
raw applicability, Definitions, Reason, Required Action(s) and Compliance
Time(s), referenced-publication, supersedure/revision/cancellation, and Remarks
wording using versioned deterministic rules.

Parser version, latency, source identity, hashes, and processing status are
stored in operational sidecars, never inside content JSON. Complex compliance
semantics are intentionally left in the original PDF passages for RAG-time
interpretation.

### 9.3 Pilot gate

Before the 1,804-document run, execute a 30-document development-only local
pilot. Record:

- parser and schema version;
- schema-valid rate;
- field-level errors;
- section-boundary errors; and
- document latency and local runtime.

Freeze the parser configuration before the full run. Corpus extraction uses no
API tokens and incurs no hosted-model cost.

### 9.4 Promotion gate

Promote a run only when:

- expected records are present;
- failures are resolved or explicitly reported;
- every JSON passes the content schema;
- no forbidden field exists;
- individual JSON and JSONL agree; and
- the canonical destination is empty.

## 10. Original-PDF retrieval architecture

### 10.1 Chunking

- Chunk the original PDF page text, not generated structured records.
- Reconstruct headings before chunking.
- Target approximately 250–450 tokens.
- Keep subordinate bullets and their parent requirement together where possible.
- Preserve tables/continuations across adjacent page chunks through metadata.
- Never combine two PDFs in one chunk.
- Store source ID, AD number, PDF name, page range, section, and lifecycle state.

### 10.2 Retrieval

The proposed E4 system uses:

1. SQLite FTS5/BM25;
2. local sentence-transformer embeddings;
3. a FAISS dense index;
4. reciprocal-rank fusion;
5. local cross-encoder reranking; and
6. metadata/lifecycle filtering.

The E0 baseline uses flat chunks and dense-only retrieval.

### 10.3 Retrieval-time compliance interpretation

For a detailed compliance question, the answer generator must:

1. use retrieved original-PDF passages;
2. include enough adjacent text to capture parent clauses and definitions;
3. preserve all material conditions and alternatives;
4. distinguish initial and repetitive requirements;
5. preserve terminating effects and exceptions;
6. avoid calculating aircraft-specific dates without aircraft history;
7. cite each material conclusion; and
8. abstain if the retrieved evidence is incomplete or conflicting.

The structured record may narrow the search but cannot independently justify a
detailed compliance answer.

## 11. QA modes

### 11.1 Corpus QA

Search the permanent original-PDF index. Answers return:

- answer text;
- AD number;
- source PDF;
- page;
- section when available; and
- insufficient-information status when necessary.

### 11.2 Temporary uploaded-PDF QA

```text
Upload unseen PDF
→ extract page text
→ create session-only chunks/index
→ answer from that PDF only
→ cite PDF/page
→ Clear Document deletes session artifacts
```

Temporary QA does not require permanent content extraction and performs no
training.

### 11.3 Permanent ingestion

```text
Explicit confirmation
→ source hash and duplicate check
→ append source PDF
→ create section-complete content record
→ create lifecycle sidecar entry
→ append original-PDF chunks to sparse/dense indexes
→ expose to corpus QA
```

Ambiguous lifecycle relationships cannot change operational selection without
review. Ingestion performs no training.

## 12. Prototype interface

The Streamlit application provides:

- **Search Corpus**;
- metadata/lifecycle filtering;
- structured metadata and raw-section view;
- original-PDF RAG question panel;
- page/source citations;
- **Upload AD**;
- temporary question panel;
- **Clear Document**;
- explicit **Add to Corpus** confirmation;
- snapshot warning; and
- insufficient-information responses.

The UI explicitly explains that compliance timing and conditional logic are
interpreted from retrieved PDF passages, not pre-structured fields.

## 13. Metrics and targets

### 13.1 Content extraction

Measure on the locked 20:

- schema validity;
- field precision, recall, and F1;
- normalized exact match;
- document coverage/failure rate;
- local runtime and latency; and
- hosted extraction tokens/cost, reported as not applicable and zero.

Targets:

- schema validity at least 98%;
- deterministic metadata core-field macro F1 at least 0.80.

Raw compliance-section wording is assessed separately for correct section
boundary and source-text containment because it is intentionally not equivalent
to the manually structured/paraphrased action units in the gold records.

### 13.2 Retrieval

Measure Recall@1/3/5, MRR, nDCG@5, and correct AD/page retrieval.

Targets:

- Recall@5 at least 0.90;
- MRR at least 0.80.

### 13.3 QA

Measure:

- answer correctness;
- complete preservation of material compliance conditions;
- correct AD selection;
- page-citation correctness;
- abstention accuracy; and
- unsupported-claim rate.

Targets:

- QA correctness at least 0.80;
- page-citation correctness at least 0.90.

Targets are planning thresholds, not claimed results.

### 13.4 Dynamic ingestion

Test five temporary uploads, isolation, clearing, duplicate rejection,
permanent index updates, lifecycle ambiguity protection, final count 1,809, and
absence of training operations.

## 14. Schedule

| Dates (2026) | Work | Exit condition |
|---|---|---|
| 4–9 Aug | Approve v3.1; validate content schema/projection; review QA v2 | Frozen active evaluation artifacts |
| 4 Aug | Run local 30-document pilot and 1,804-document extraction | 1,804 schema-valid records; zero hosted calls |
| 10–16 Aug | Review deterministic metadata/section quality | Error analysis and frozen parser rules |
| 17–23 Aug | Prepare original-PDF page text and retrieval inputs | Page-preserving source derivatives |
| 24–30 Aug | Build original-PDF chunks and local indexes | Page-aware E0/E4 indexes |
| 31 Aug–6 Sep | Evaluate retrieval | Retrieval metrics/error report |
| 7–13 Sep | Evaluate corpus and temporary QA, especially compliance logic | QA/citation/abstention report |
| 14–20 Sep | Permanent ingestion and final evaluation | Five ingestions; count 1,809 |
| 21–27 Sep | UI, error analysis, thesis, documentation | Reviewable final system |
| 28–30 Sep | Reproduction, presentation, demonstration | Final package |

## 15. Verification checklist

### Active content evaluation data

- [x] Immutable audit release unchanged.
- [x] Exactly 50 content JSON records and 50 JSONL lines.
- [x] Difficult sections retained without machine-normalized compliance structures.
- [x] No evidence, review, benchmark, confidence, status, machine, or source
  fields in content records.
- [x] Every retained scalar has projection lineage.
- [x] 30/20 split frozen with seed 42.
- [x] QA v2 contains exactly 50 questions.
- [x] Five unseen PDF families remain locked and disjoint.

### Full execution

- [ ] Human spot review of content records and QA v2 references.
- [ ] Supervisor approval of v3.
- [x] 30-document local development pilot.
- [x] 1,804 section-complete development records with zero failures.
- [ ] Original-PDF page-aware E0 and E4 indexes.
- [ ] Locked extraction, retrieval, and QA evaluation.
- [ ] Five temporary and permanent ingestion tests.
- [ ] Final count of 1,809.

### Repository

- [x] Unit tests and validators pass.
- [x] Markdown links and `git diff --check` pass.
- [ ] Frozen sources, queues, and gold releases remain unchanged.
- [ ] Unrelated working-tree changes remain preserved.

## 16. Commands

Generate the active content projection:

```bash
.venv/bin/python -m full_corpus_pipeline.content_projection
.venv/bin/python -m full_corpus_pipeline.freeze_evaluation_design
.venv/bin/python -m full_corpus_pipeline.validate_content_dataset \
  evaluation_sets/easa_airbus_ad_content_gold_50_v2 \
  --expected-count 50
```

Build and validate QA v2:

```bash
.venv/bin/python -m full_corpus_pipeline.build_qa_benchmark
.venv/bin/python -m full_corpus_pipeline.validate_qa_benchmark
```

Run the local development pilot:

```bash
.venv/bin/python -m full_corpus_pipeline.extract_corpus \
  --evaluation-split development \
  --run-id local-content-pilot-30-v2
```

Run and validate the 1,804-document development extraction:

```bash
.venv/bin/python -m full_corpus_pipeline.extract_corpus \
  --run-id local-content-development-1804-v2.1.3

.venv/bin/python -m full_corpus_pipeline.validate_content_dataset \
  data_processed/runs/local-content-development-1804-v2.1.3 \
  --expected-count 1804
```

Build the original-PDF hybrid index:

```bash
.venv/bin/python -m full_corpus_pipeline.retrieval \
  --page-text-dir /approved/page_text \
  --manifest step3_pilot/source_metadata/corpus_manifest.parquet \
  --exclude-selection evaluation_sets/unseen_incoming_5_v1/selection.csv \
  --output-dir indexes/corpus_v1
```

Run verification:

```bash
.venv/bin/python -m unittest discover -s full_corpus_pipeline/tests -v
git diff --check
```

## 17. Immediate next actions

1. Obtain supervisor approval for the v3 two-layer methodology.
2. Human spot-check the content 50 and QA v2 references.
3. Review the completed local pilot and freeze parser v2.1.3.
4. Preserve `data_processed/canonical_content_v2.1.3/` as the active generated corpus.
5. Build original-PDF page-aware retrieval indexes.
6. Evaluate whether RAG preserves complex compliance logic at question time.
7. Test temporary/permanent ingestion and finish with 1,809 records.

## 18. Proposal-ready methodology summary

This capstone processes a frozen snapshot of 1,809 Airbus S.A.S. EASA AD PDF
records using a two-layer architecture. A deterministic local parser creates a
section-complete catalogue containing structured reliable metadata and raw
Applicability, Definitions, Reason, Required Action(s) and Compliance Time(s),
referenced-publication, supersedure/revision/cancellation, and Remarks content.
Complex compliance timing,
conditions, exceptions, repetitive intervals, follow-on actions, and
terminating effects are deliberately not normalized across the full corpus.
Instead, a section-aware hybrid RAG system retrieves original PDF page text and
an LLM interprets the complete regulatory wording at question time with
page-level citations and abstention. The existing validated 50-record release is
preserved as an immutable audit source, while a separate content-only 30/20
evaluation projection and 50-question QA v2 benchmark measure extraction,
retrieval, compliance interpretation, citations, and abstention. Five non-gold
PDFs are held out from the 1,804-document development corpus to test temporary
QA and permanent ingestion without retraining, producing the final 1,809-record
corpus. The prototype supports engineering review but does not determine legal
compliance or authorize maintenance.
