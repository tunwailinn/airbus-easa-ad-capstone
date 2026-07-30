---
title: "Exact Project Plan"
subtitle: "Intelligent Engineering Document Automation for Aviation Maintenance: Airbus S.A.S. Airworthiness Directives Issued by EASA"
author: "Prepared for Tun Wai Lin"
date: "Version 1.3 - 30 July 2026"
subject: "11-week capstone research and implementation plan"
keywords:
  - Airworthiness Directives
  - EASA
  - Airbus S.A.S.
  - Natural Language Processing
  - Retrieval-Augmented Generation
---

**Proposed execution period:** 13 July-30 September 2026 (11 full weeks plus 3 final submission days)

> **Project goal:** Build and evaluate a version-aware, evidence-grounded AI assistant that converts Airbus S.A.S. EASA Airworthiness Directives (ADs) into structured maintenance-compliance information and answers questions using the correct AD version with page-level evidence.

---

# 1. Executive decision

The project will not begin by putting all PDFs directly into a vector database. The approximately 1,800 PDFs will first be converted into a controlled, version-aware corpus. The system will then extract maintenance requirements, classify actions, generate evidence-grounded summaries, and support hybrid retrieval and question answering.

The proposed research contribution is the integration of:

1. corpus governance;
2. AD revision, correction, and supersedure modelling;
3. structured compliance-unit extraction;
4. version-aware hybrid retrieval;
5. evidence-grounded answer generation; and
6. evaluation against a manually annotated Airbus EASA AD benchmark.

The final system is a research prototype for maintenance decision support. It is not an approval authority, compliance-signoff system, or replacement for licensed engineering judgment.

The fixed core evaluation package is:

| Artifact | Core target | Optional stretch target |
|---|---:|---:|
| Manually annotated ADs | 100 | 200 total |
| Locked evaluation questions | 150 | No expansion required |
| Human reference summaries | 30 | 50 total |

The core targets take priority. Stretch annotation starts only after the 100-AD dataset has passed validation and the locked test benchmark has been frozen.

Step 3 reaches that core through controlled, versioned release checkpoints:

| Step 3 release checkpoint | Role |
|---|---|
| Frozen 30-record pilot | First independently reviewed and strictly validated release |
| Separate 20-record batch | Current source-verified, machine-assisted review batch; non-gold until explicit human approval |
| Combined 50-record release | New version containing the preserved 30 plus the separately approved 20 |
| Fixed 100-record core | Final core benchmark used for the 60/20/20 family-level split |

The 30- and 50-record releases are intermediate delivery checkpoints toward the 100-record core. They are not the optional expansion from 100 to 200.

For every Step 3 annotation batch and release, `docs/PDF_TO_GOLD_FRAMEWORK.md` is authoritative. A validator can prove structure and evidence consistency, but it cannot grant human approval.

---

# 2. Fixed project scope

## 2.1 Included

- Final Airworthiness Directives issued by the European Union through EASA.
- Approval holder/type designation: **Airbus S.A.S.**
- Airbus aeroplane families represented in the available corpus, such as A300/A310, A318/A319/A320/A321, A330/A340, A350, and A380.
- Original ADs, emergency ADs, revisions, corrected publications, and superseded historical versions.
- English-language PDF content and metadata available from the EASA Safety Publications Tool.
- Extraction, classification, summarization, retrieval, question answering, citation, and version selection.

## 2.2 Excluded from the main experimental corpus

- Proposed Airworthiness Directives (PADs).
- Safety Information Bulletins (SIBs).
- ADs issued by authorities other than the EU, even when EASA lists or adopts them.
- Airbus Helicopters, Airbus Canada, engines, and components whose approval holder is not Airbus S.A.S.
- Service Bulletins as primary documents. Their identifiers will be extracted as references, but their full content will not be indexed unless the scope is formally extended.
- Automatic determination of whether a particular physical aircraft is legally compliant.
- Maintenance planning, work-order generation, or release-to-service authorization.

## 2.3 Two controlled corpus views

| Corpus view | Contents | Purpose |
|---|---|---|
| Historical view | All verified originals, revisions, corrections, and superseded versions | Traceability, lifecycle research, and historical questions |
| Operational view | One canonical, latest applicable publication per AD family | Default retrieval and current-requirement questions |

The raw PDFs remain immutable. A document is excluded from an experimental view through metadata, not by deleting the original file.

---

# 3. Research objective and questions

## 3.1 Primary objective

Develop an AI-powered AD automation framework that reliably extracts, classifies, summarizes, and retrieves maintenance information from Airbus S.A.S. EASA ADs while preserving document lifecycle, provenance, and evidence.

## 3.2 Research questions

**RQ1 - Structured extraction:**  
How accurately can deterministic parsing and schema-constrained language models extract applicability, unsafe conditions, required actions, compliance thresholds, repetitive intervals, terminating actions, and referenced publications from Airbus EASA ADs?

**RQ2 - Version awareness:**  
How much does explicit modelling of revisions, corrections, and supersedure improve selection of the current AD and reduce retrieval of outdated requirements?

**RQ3 - Retrieval:**  
Does hybrid retrieval combining metadata filters, BM25, dense embeddings, reciprocal-rank fusion, and reranking outperform flat dense-only retrieval?

**RQ4 - Answer reliability:**  
Can evidence-constrained generation provide correct, faithful, page-cited answers and abstain when the retrieved AD evidence is insufficient or conflicting?

## 3.3 Testable hypotheses

- **H1:** The hybrid extraction pipeline will outperform deterministic rules alone on semantic maintenance fields.
- **H2:** The full hybrid retriever will achieve higher Recall@5 and MRR than a dense-only, flat-chunk baseline.
- **H3:** Version filtering will significantly reduce stale-version retrieval errors.
- **H4:** Generating from verified evidence and structured compliance units will reduce unsupported claims compared with generic RAG.

---

# 4. Target system behaviour

The user can ask questions such as:

- “What action is required by EASA AD 2023-0167R1?”
- “Which current A320 ADs require repetitive inspection?”
- “What is the initial compliance threshold and repetitive interval?”
- “Is this AD revised, corrected, or superseded?”
- “What changed between the original AD and R1?”

For every answer, the system must:

1. resolve the requested AD or aircraft scope;
2. determine whether the query is current or historical;
3. filter to the correct document version;
4. retrieve the relevant section and paragraph;
5. answer only from retrieved evidence;
6. cite the AD number, version, page, and section;
7. warn when an older or superseded version is involved; and
8. abstain when the evidence is missing, contradictory, or below the confidence threshold.

The assistant must never silently combine requirements from different revisions.

---

# 5. Research methodology

The study will use a **design-science and experimental evaluation** methodology:

1. **Problem analysis:** identify the limitations of manual AD review and ordinary PDF-based RAG.
2. **Artifact design:** build the controlled corpus, extraction schema, compliance records, retriever, and assistant.
3. **Artifact implementation:** implement the reproducible processing and inference pipelines.
4. **Controlled evaluation:** compare baselines, the proposed method, and ablated variants on a locked gold test set.
5. **Error analysis:** categorize failures and revise only using training/development data.
6. **Demonstration:** provide a working assistant with traceable evidence and documented limitations.

The unit of dataset splitting is the **base AD family**, not an individual PDF. All versions of one base AD must remain in the same train, development, or test partition to prevent leakage.

---

# 6. Exact implementation plan

## 6.1 Build the corpus manifest and automatic audit

### Objective

Transform the raw PDF folder into a reproducible inventory with one row per physical file.

### Actions

1. Discover all PDFs recursively without modifying them.
2. Assign a stable `file_instance_id`.
3. calculate SHA-256 for file bytes and normalized extracted text.
4. extract PDF metadata, page count, text length, and extraction status.
5. detect AD number, base number, revision number, emergency status, issue date, and correction notice.
6. detect exact binary duplicates and exact-text duplicates.
7. identify same-version/different-content conflicts.
8. build original-revision-correction chains.
9. identify candidate supersedure links and retain evidence snippets.
10. flag low-text, damaged, protected, scanned, unparsed, or non-Airbus files.
11. create a separate `manual_overrides.csv`; never edit generated metadata by hand.

### Outputs

- `corpus_manifest.xlsx`, `.csv`, and `.parquet`
- `corpus_extracted_text.parquet`
- `duplicate_review.csv`
- `version_chains.csv`
- `near_duplicate_candidates.csv`
- `supersedure_links.csv`
- `processing_and_metadata_review.csv`
- `manual_overrides.csv`
- `corpus_summary.json`

### Completion gate G1-A

- Every PDF has one unique manifest row and a file hash.
- At least 95% of AD numbers are parsed automatically, or every failure is manually queued.
- Exact duplicates are grouped.
- Revisions and corrections are represented as different logical versions.
- No original file has been deleted, renamed, or overwritten.

---

## 6.2 Validate, OCR, and create the canonical corpus

### Objective

Convert automatic candidates from 6.1 into verified corpus decisions.

### Review order

1. Review corpus-level counts in `corpus_summary.json`.
2. Resolve missing AD numbers and non-Airbus detections.
3. OCR every flagged scanned PDF and compare OCR text with the visible page.
4. confirm exact duplicate groups and select one canonical physical copy.
5. inspect same-version/different-content conflicts.
6. verify revision and correction order.
7. verify each supersedure sentence in its full context.
8. record all decisions in `manual_overrides.csv`.
9. apply overrides through code to generate a new, reproducible canonical view.

### Canonical selection rules

- Keep one physical master for byte- or text-identical copies.
- Keep every substantively different original, revision, correction, and emergency issue.
- Prefer the corrected publication over the uncorrected copy of the same revision in the operational view.
- Prefer the highest verified revision unless it has been superseded by another AD.
- Never discard a conflicting same-version file automatically.
- Preserve the historical version even when it is excluded from default retrieval.

### Outputs

- `canonical_manifest.parquet`
- `canonical_historical_documents.parquet`
- `canonical_operational_documents.parquet`
- `verified_version_chains.csv`
- `verified_supersedure_links.csv`
- `ocr_quality_report.csv`
- completed `manual_overrides.csv`

### Completion gate G1-B

- 100% of included files have a confirmed AD identity.
- 100% of operational documents have a verified lifecycle state.
- No unresolved same-version conflict enters the operational index.
- OCR samples show readable AD number, section headings, and compliance paragraphs.
- A corpus flow count explains every inclusion and exclusion.

---

## 6.3 Govern the structured schema and Step 3 PDF-to-gold workflow

### Objective

Specify exactly what the AI must extract, how a human reviewer decides the correct value, and how a selected PDF moves through controlled review into an immutable versioned gold release.

`docs/PDF_TO_GOLD_FRAMEWORK.md` version 1.0.0 is authoritative for Step 3. The versioned Step 2 schema and annotation guidance define annotation meaning:

- `step2_ad_schema/easa_airbus_ad_annotation.schema.json`
- `step2_ad_schema/annotation_guidelines.md`
- `step2_ad_schema/controlled_vocabularies.json`
- `step2_ad_schema/blank_ad_annotation.json`
- `step2_ad_schema/validate_annotations.py`

Any schema or guideline change requires a new version, changelog entry, regression validation of existing gold, and an explicit migration decision.

### Required schema

| Group | Required fields |
|---|---|
| Identity | AD number, base AD number, revision, emergency flag, correction flag/date |
| Dates/status | Issue date, effective date, lifecycle status, supersedes, superseded by |
| Aircraft | family, model/variant, serial range, configuration, affected part |
| Safety context | ATA chapter, subject, reason, unsafe condition, consequence |
| Compliance unit | condition, required action, method, initial threshold, repeat interval, terminating action, exceptions |
| References | Service Bulletin and other publication identifiers and versions |
| Provenance | file ID, page, section, paragraph/span, extraction confidence, review state |

A compliance unit is the central research object:

```json
{
  "unit_id": "2023-0167R1-CU-01",
  "applicability_condition": "Aeroplanes with an affected main landing gear axle installed",
  "required_action": "Perform the specified inspection",
  "initial_compliance": {
    "value": 1200,
    "unit": "flight_cycles",
    "reference_event": "AD effective date"
  },
  "repetitive_interval": {
    "value": 1200,
    "unit": "flight_cycles"
  },
  "terminating_action": null,
  "referenced_publications": ["Airbus SB ..."],
  "evidence": [
    {
      "page": 4,
      "section": "Required Action(s) and Compliance Time(s)",
      "text": "..."
    }
  ]
}
```

### Annotation rules

- Copy the technical meaning; do not simplify away conditions or exceptions.
- Split two actions into separate compliance units when their applicability or timing differs.
- Normalize dates and units while retaining the original text.
- Use `not_stated` rather than guessing.
- Attach evidence page and span to every non-derived field.
- Mark ambiguous content for adjudication.
- Distinguish “within 30 days” from “before next flight,” “before exceeding X cycles,” and repetitive intervals.
- Do not infer model applicability from the title when the applicability section is more restrictive.

### Non-negotiable Step 3 rules

1. Treat `corpus_raw`, frozen selections, canonical sources, and `human_review_queue/` as read-only.
2. Freeze filename, source URL, PDF SHA-256, page count, `file_instance_id`, `content_id`, and normalized-text SHA-256 before annotation.
3. Review the complete canonical PDF, including tables, appendices, footnotes, diagrams, scans, and multi-column text.
4. Trace every populated safety-relevant value to page-grounded evidence.
5. Make review corrections only in `human_review_working/`.
6. Do not infer human approval from extraction, validation, file location, or a request to copy files.
7. Do not set `creation_method=manual`, `record_status=approved`, `classification.human_confirmed=true`, or `benchmark_metadata.gold_record=true` without explicit independent human approval.
8. Publish approved records only in a new versioned release; never overwrite a previous release.
9. Declare a release complete only after Drive readback verifies exact membership, filenames, hashes, representative content, and the final validation report.

### Required lifecycle

The allowed transition is linear:

```text
selected
  -> source_verified
  -> machine_first_pass
  -> human_review_pending
  -> human_review_in_progress
  -> human_approved
  -> gold_validated
  -> gold_published
```

No script may jump directly from machine output to gold.

### Current Step 3 release progression

- **Frozen 30-record pilot:** 30 canonical PDFs and 171 pages, including 10 designated double annotations. The current approved working records pass the pilot validator, the reusable release validator, and evidence validation with zero errors. Preserve or import the exact versioned release package and its Drive readback evidence; do not mutate the earlier release.
- **Separate 20-record batch:** the frozen sources, page text, packets, immutable queue, and editable working copies exist. The populated candidates pass non-strict schema/semantic and evidence checks but remain `creation_method=hybrid`, `record_status=first_pass_complete`, `human_confirmed=false`, and `gold_record=false` until explicit independent review and approval.
- **Combined 50-record release:** create only after the 20 records are independently approved and strictly validated. It must be a new version equal to the preserved 30 plus approved 20; it must not replace the 30-record release.
- **Fixed 100-record core:** continue from the 50-record checkpoint using the same framework, then freeze the 60/20/20 family-level split.

### Step 3 validation sequence

After explicit human approval, run:

```bash
python3 step2_ad_schema/validate_annotations.py --strict \
  <working-folder>/*.annotation.json

python3 step3_pilot/validate_evidence_quotes.py \
  <working-folder> \
  --page-text-dir <page-text-folder>

python3 dataset_framework/validate_gold_release.py \
  <working-folder> \
  --selection <frozen-selection.json> \
  --source-pdf-dir <source-pdf-folder> \
  --page-text-dir <page-text-folder> \
  --expected-count <count> \
  --report <validation-report.json>
```

Use `step3_pilot/validate_step3_pilot.py` only for the exact frozen 30-record pilot because it hard-codes the 30-record membership, 15+15 cohort design, and double-annotation requirements. Use the reusable release validator for the separate 20-record batch, combined 50-record release, fixed 100-record core, and any later release.

### Outputs

- Versioned Step 2 schema, guidelines, controlled vocabularies, template, changelog, and validators
- `step3_pilot/` frozen selection, sources, submissions, adjudication records, approved working annotations, and validation reports
- `step3_extension_20_v1/` frozen selection, sources, packets, queue, working copies, and validation reports
- `dataset_framework/BATCH_CHECKLIST.md`
- `dataset_framework/script_registry.json`
- `dataset_framework/validate_gold_release.py`
- Versioned `gold_releases/<release-id>/` packages containing exact selections, annotations, manifests, source manifests, validation reports, and release notes

### Completion gate G2

- Frozen selection membership and canonical source identity pass for the exact batch.
- PDF hashes, page counts, page-text cache, and complete-page visual review pass.
- Machine candidates pass non-strict schema/semantic and evidence validation before entering the immutable queue.
- Every field assertion and substantive section is independently reviewed in the working copy.
- Explicit approval provenance and final manual/approved/human-confirmed/gold states are complete.
- Strict schema/semantic and evidence validation return zero errors.
- `dataset_framework/validate_gold_release.py` passes all five release gates with zero errors.
- The versioned release preserves earlier releases and passes exact Drive readback.

---

## 6.4 Create the manually annotated gold dataset

### Objective

Create ground truth for extraction, classification, summarization, retrieval, and question-answering evaluation.

### Sample

Select **100 logical AD versions** using stratified, family-aware sampling. This is the fixed core gold dataset for the compressed project period:

| Primary selection bucket | Target |
|---|---:|
| Ordinary latest ADs | 50 |
| Revisions or corrected issues | 20 |
| Emergency ADs | 10 |
| Superseded/historical versions | 10 |
| OCR-heavy or structurally complex ADs | 10 |
| **Total** | **100** |

If a document belongs to several buckets, assign one primary bucket for quota accounting and retain all secondary tags.

Maintain coverage across aircraft families, ATA chapters, document length, action type, and compliance complexity.

### Step 3 release checkpoints within the core

The core is assembled through immutable releases:

1. Preserve the frozen 30-record pilot release.
2. Independently review and publish the separate 20-record batch.
3. Publish a new combined 50-record release containing the preserved 30 plus approved 20.
4. Select, review, and publish the remaining records required for the fixed 100-record core.

Each batch keeps its own frozen selection, canonical source PDFs, page-text cache, immutable review queue, editable working folder, validation reports, and audit trail. A combined release is a new dataset version, not a mutation of either input release.

If time remains after the core dataset passes validation, annotate up to **100 additional ADs**, producing a 200-AD extended gold set. The extension must:

- follow the same schema, sampling rules, and review process;
- contain no `base_ad_number` already assigned to another partition;
- remain separate as `gold_extension_v1` until validation is complete;
- preserve the original locked 20-document core test set; and
- be reported as a stretch deliverable rather than a prerequisite for project completion.

### Split

- Training/prompt-development: 60 documents
- Development/model-selection: 20 documents
- Locked test: 20 documents

Split by `base_ad_number`. Freeze the test IDs before model development begins.

If the optional second 100 ADs are completed, assign 70 to training, 10 to development, and 20 to a separately locked extension test set. Report core-test and extension-test results separately before any pooled result.

### Quality control

- A second reviewer checks at least 20% of documents.
- If a second reviewer is unavailable, re-annotate the 20% sample after a delay and clearly report this limitation.
- Use Cohen's kappa for categorical labels.
- Use span/tuple F1 or Jaccard agreement for extracted fields and compliance units.
- Adjudicate disagreements and document every rule change.
- Version the annotations; never silently overwrite labels.
- Keep frozen selections and review queues read-only.
- Make annotation corrections only in the batch `human_review_working/` folder.
- Require explicit independent approval before assigning manual, approved, human-confirmed, or gold state.
- Run strict schema validation, evidence validation, and `dataset_framework/validate_gold_release.py` against the exact selection and sources.
- Publish only new versioned releases and verify each published release by Drive readback.

### Additional benchmarks

Create **150 questions**:

| Question type | Count |
|---|---:|
| Identity and lifecycle status | 25 |
| Aircraft applicability | 25 |
| Required action and compliance time | 40 |
| Referenced publications | 15 |
| Revision/supersedure questions | 20 |
| Multi-passage synthesis questions | 15 |
| Insufficient-evidence, conflict, or abstention questions | 10 |
| **Total** | **150** |

Each question contains the answer, acceptable variants, supporting AD/version, page, evidence span, question type, difficulty, and whether abstention is expected.

Create **30 human reference summaries**. This is sufficient for a focused capstone evaluation because each reference requires whole-document synthesis and evidence checking, while the 150-question set provides broader retrieval and QA coverage.

Select the 30 summaries from development and locked-test documents using a stratified design:

| Summary stratum | Count |
|---|---:|
| Ordinary latest ADs | 10 |
| Revised or corrected ADs | 6 |
| Emergency ADs | 4 |
| Superseded or historical ADs | 4 |
| Complex multi-action/compliance ADs | 4 |
| OCR-heavy or structurally difficult ADs | 2 |
| **Total** | **30** |

Each reference summary must be written or fully verified by a human, cite its supporting pages, cover every safety-critical condition/action/time relationship, and avoid adding facts that are not in the AD. If time remains, expand the summary set to **50** using the same strata and quality controls.

### Outputs

- `gold_ad_records_v1.jsonl`
- `dataset_splits_by_family.csv`
- `qa_benchmark_v1.jsonl`
- `reference_summaries_v1.jsonl`
- `annotation_agreement_report.md`
- `benchmark_lock_manifest.json`
- versioned `gold_releases/` packages with selections, annotations, source/annotation manifests, final validation reports, release notes, and Drive readback metadata

### Completion gate G3

- All 100 records pass schema validation.
- Every 30-, 20-, 50-, and 100-record Step 3 release passes the PDF-to-gold framework gates appropriate to its exact frozen selection.
- Automated validation is not treated as human approval.
- Every release passes strict schema/semantic validation, evidence validation, and the reusable release validator with zero errors.
- Drive readback confirms exact membership, filenames, hashes, representative JSON content, and the final validation report.
- Earlier releases remain unchanged and available for audit.
- Any optional extension records pass the same validation before inclusion in a new versioned combined release.
- No base AD family crosses dataset splits.
- Every gold answer and extracted field has evidence.
- The test set is locked and is not used for prompt or model selection.
- All 150 questions and 30 reference summaries pass independent evidence checks.

---

## 6.5 Reconstruct sections and create semantic chunks

### Objective

Preserve the AD's regulatory structure during indexing.

### Processing

1. Extract text page by page.
2. remove repeated headers, footers, page numbers, and EASA boilerplate only through reviewed rules.
3. reconstruct paragraphs and lists without losing paragraph identifiers.
4. identify sections such as Applicability, Definitions, Reason, Required Action(s) and Compliance Time(s), Ref. Publications, and Remarks.
5. preserve tables as row-aware text and retain page coordinates where possible.
6. create parent section nodes and smaller child chunks.

### Chunking configuration

- **Proposed method:** section-aware child chunks of 250-450 tokens, approximately 15% overlap only within a section.
- Keep one compliance paragraph and its subordinate bullets together.
- Attach parent heading path, AD number, base family, lifecycle status, aircraft model, ATA chapter, page range, and canonical status.
- Never combine text from two documents or revisions.
- **Baseline:** flat 500-token chunks with 100-token overlap and no lifecycle filtering.

### Quality sample

Visually compare reconstructed text and chunks for at least 30 documents, including 10 with tables or complex compliance paragraphs.

### Outputs

- `document_sections.parquet`
- `rag_chunks.parquet`
- `chunk_quality_review.csv`
- reproducible preprocessing configuration

### Completion gate G4

- At least 95% of reviewed chunks preserve their correct section and AD version.
- No reviewed compliance condition is separated from its required action.
- Page references survive preprocessing.

---

## 6.6 Develop the structured information-extraction pipeline

### Objective

Convert each AD into validated JSON and repeatable compliance units.

### Three-stage extractor

**Stage A - Deterministic parser**

- Parse document identifiers, dates, headings, ATA chapter, publication references, and explicit revision/correction markers.
- Normalize common aircraft model and time-unit formats.

**Stage B - Schema-constrained language model**

- Extract semantic fields: applicability conditions, unsafe condition, consequence, action, compliance timing, repetitive interval, exceptions, and terminating action.
- Require strict JSON matching the schema.
- Use temperature 0 and store model name, model revision, prompt version, token usage, latency, and raw response.

**Stage C - Validator and evidence checker**

- Validate JSON types and required fields.
- Check that quoted evidence exists on the cited page.
- verify normalized numbers and units against the source span.
- flag contradictions, missing evidence, invalid model names, and impossible date order.
- route low-confidence or invalid records to human review.

### Model-selection experiment

Compare at least:

1. deterministic rules only;
2. zero-shot schema-constrained extraction;
3. few-shot extraction using training examples; and
4. an open-source instruction model if available compute permits.

Choose the primary model on the 20-document development set using this decision rule:

1. schema validity must be at least 98%;
2. evidence support must be at least 95%;
3. among qualifying models, select the highest compliance-unit F1;
4. if F1 differs by less than one percentage point, select the lower-cost/faster model.

Do not fine-tune initially. Fine-tuning becomes a separate experiment only if few-shot extraction misses the development target and adequate labelled examples exist.

### Outputs

- `extracted_ad_records.jsonl`
- `extraction_review_queue.csv`
- `normalization_dictionary.json`
- prompt and model configuration files
- experiment logs

### Completion gate G5

- Development schema-valid response rate >= 98%.
- Development macro F1 across core fields >= 0.85.
- Development compliance-unit tuple F1 >= 0.80.
- Every accepted semantic field has source evidence.

These values are acceptance targets, not results to claim before evaluation.

---

## 6.7 Build the classification module

### Objective

Assign consistent maintenance-oriented labels without using a model for facts already determined by the manifest.

### Label design

Use multi-label action categories:

- inspection;
- replacement;
- modification;
- repair;
- operational limitation;
- AFM amendment;
- maintenance-program/ALS amendment;
- software update;
- repetitive action;
- terminating action; and
- reporting/recording action.

Aircraft family, ATA chapter, and lifecycle status are extracted or derived from authoritative metadata; they are not guessed by the classifier.

### Experiments

1. keyword/rule baseline;
2. TF-IDF plus one-vs-rest logistic regression baseline;
3. transformer or embedding-based classifier if the baseline is insufficient;
4. classification from full text versus extracted action spans.

### Evaluation

- Per-label precision, recall, and F1
- Micro F1 and macro F1
- Exact-match ratio
- Confusion/error analysis for rare labels

### Output and gate G6

- `classification_labels.json`
- trained pipeline and configuration
- classification report and confusion analysis
- target macro F1 >= 0.85 on the locked test set

---

## 6.8 Generate evidence-grounded summaries

### Objective

Produce concise, maintenance-focused summaries without losing conditions or inventing requirements.

### Summary format

1. AD identity and status
2. affected aircraft/applicability
3. unsafe condition and consequence
4. required actions
5. initial compliance time
6. repetitive interval
7. terminating action
8. referenced publications
9. version/supersedure warning
10. evidence citations

Generate the summary from validated structured fields plus retrieved evidence, not from the entire PDF without controls. If a field is absent, output “Not stated in the retrieved AD evidence.”

### Evaluation

- Field coverage against the gold record
- factual correctness
- faithfulness to evidence
- omission of critical conditions
- unsupported-claim rate
- citation correctness
- optional ROUGE-L/BERTScore as secondary measures only
- blinded human rating of all 30 core reference-summary cases on a 1-5 rubric

### Output and gate G7

- `generated_summaries.jsonl`
- summary prompt/template
- human-evaluation form
- target evidence faithfulness >= 95% and unsupported-claim rate <= 5%

---

## 6.9 Build the version-aware hybrid retrieval system

### Objective

Retrieve the correct evidence while preventing outdated versions from appearing in current-requirement answers.

### Retrieval pipeline

1. **Query analysis:** detect AD number, aircraft family/model, ATA chapter, action type, date, and explicit historical intent.
2. **Version policy:** default to operational/latest documents; use the historical view only when the query names an older version or asks about changes/history.
3. **Sparse retrieval:** BM25 for exact identifiers and technical terms.
4. **Dense retrieval:** embedding similarity for natural-language meaning.
5. **Fusion:** reciprocal-rank fusion (initial constant `k = 60`).
6. **Reranking:** rerank the fused top 30 candidates.
7. **Evidence selection:** pass the best 5 diverse, non-duplicate chunks to generation.

### Initial reproducible configuration

| Component | Initial choice |
|---|---|
| Metadata/records | Parquet plus SQLite |
| Sparse index | BM25 |
| Dense index | FAISS |
| Embedding pilot | `BAAI/bge-base-en-v1.5` |
| Comparator embedding | `intfloat/e5-base-v2` |
| Reranker pilot | `BAAI/bge-reranker-base` |
| Fusion | Reciprocal-rank fusion, `k = 60` |
| Initial candidate depth | 30 sparse + 30 dense |
| Final evidence | Up to 5 chunks |

Freeze the selected embedding and reranker revisions after development-set comparison. Record all versions and random seeds.

### Mandatory version policy

- Current/default query: `canonical = true`, `is_latest = true`, and `superseded = false`.
- Explicit revision query: retrieve that exact revision and display a historical warning.
- Correction: use the corrected publication over the uncorrected copy of the same revision.
- Ambiguous or conflicting lifecycle metadata: abstain and present the conflict for review.
- Revision comparison: retrieve matched sections from both requested versions and label each passage clearly.

### Retrieval baselines

- B1: keyword/BM25 only
- B2: dense-only flat chunks
- B3: hybrid retrieval without reranking
- Proposed: metadata + version filter + section-aware BM25/dense fusion + reranking

### Output and gate G8

- version-aware retrieval service
- indexed historical and operational views
- retrieval experiment report
- target Recall@5 >= 0.90 and MRR >= 0.80
- target latest-version selection accuracy >= 0.98, with a research goal of 1.00

---

## 6.10 Implement the evidence-grounded assistant

### Objective

Expose extraction, search, summarization, and QA through one demonstrable interface.

### Minimum interface

- AD number search
- filters for aircraft family, model, ATA chapter, action type, and status
- current/historical mode
- structured AD record
- maintenance-focused summary
- question-answering panel
- citations that open the source page
- visible version chain and supersedure warning
- “insufficient evidence” response state
- user feedback button for incorrect extraction or answer

### Answer contract

Every response must contain:

- direct answer;
- AD number and exact version;
- current/historical status;
- supporting page and section citations;
- uncertainty or conflict warning when applicable; and
- disclaimer that the source AD remains authoritative.

### Output and gate G9

- working local or hosted research prototype
- API documentation
- user guide
- 20 end-to-end acceptance tests covering current, historical, no-answer, and conflict cases

---

## 6.11 Evaluate, ablate, and analyse errors

### Extraction evaluation

- exact match for AD numbers, dates, and publication identifiers;
- normalized precision, recall, and F1 for aircraft and semantic fields;
- tuple-level F1 for complete compliance units;
- evidence-span correctness;
- schema-valid output rate.

### Retrieval evaluation

- Recall@1, Recall@3, Recall@5;
- MRR;
- nDCG@5;
- latest-version selection accuracy;
- stale-version retrieval rate;
- evidence page recall.

### Answer and summary evaluation

- answer correctness: correct/partially correct/incorrect;
- faithfulness and unsupported-claim rate;
- citation precision and citation recall;
- critical-condition omission rate;
- correct abstention and false-abstention rate;
- human usefulness/readability rating.

### Required ablations

| Experiment | Removed component | Purpose |
|---|---|---|
| A1 | Version/lifecycle filter | Measure outdated-document risk |
| A2 | Structured metadata filters | Measure contribution of exact AD attributes |
| A3 | BM25 branch | Measure dense-only performance |
| A4 | Dense branch | Measure sparse-only performance |
| A5 | Reranker | Measure second-stage ranking value |
| A6 | Section-aware chunks | Compare with flat chunking |
| A7 | Structured compliance records | Measure value of structured grounding |

### Statistical reporting

- Report means and 95% bootstrap confidence intervals.
- Use paired question-level comparisons between baseline and proposed methods.
- Report corpus counts and excluded cases, not only aggregate scores.
- Never tune prompts or thresholds on the locked test set.

### Error taxonomy

- PDF/OCR error
- section reconstruction error
- lifecycle/version error
- applicability boundary error
- action-condition linking error
- time-unit normalization error
- reference extraction error
- retrieval miss
- reranking error
- unsupported generation
- incorrect citation
- unnecessary or missed abstention

### Output and gate G10

- `evaluation_results.csv`
- ablation tables and figures
- error-analysis report with representative cases
- reproducible evaluation script
- explicit statement of which acceptance targets were and were not met

---

## 6.12 Finalize the thesis, reproducibility package, and demonstration

### Thesis/report structure

1. Introduction and problem statement
2. Aviation and AD background
3. Literature review and research gap
4. Proposed version-aware framework
5. Dataset and annotation methodology
6. System implementation
7. Experimental design
8. Results
9. Error analysis and discussion
10. Limitations, safety considerations, and future work
11. Conclusion

### Final outputs

- cleaned and documented corpus metadata;
- gold annotation and QA benchmark;
- extraction, classification, summarization, and retrieval code;
- configuration and prompt versions;
- evaluation scripts and results;
- working assistant demo;
- installation and user documentation;
- final dissertation/report;
- presentation and recorded demo;
- limitations and ethical/safety statement.

### Completion gate G11

Another student should be able to rebuild the manifest, apply the recorded overrides, recreate both indexes, and reproduce the reported metrics using the documented commands and frozen configurations.

---

# 7. Experiment matrix

| ID | System | Chunking | Retrieval | Lifecycle filter | Grounding |
|---|---|---|---|---|---|
| E0 | Generic RAG baseline | Flat | Dense only | No | Retrieved text |
| E1 | Sparse baseline | Flat | BM25 | No | Retrieved text |
| E2 | Hybrid baseline | Flat | BM25 + dense | No | Retrieved text |
| E3 | Version-aware hybrid | Section-aware | BM25 + dense + reranker | Yes | Retrieved text |
| E4 | Full proposed system | Section-aware | Hybrid + reranker | Yes | Structured record + evidence |

Primary comparison: **E0 versus E4**.  
Component contribution: **E1/E2/E3 versus E4** and ablations A1-A7.

---

# 8. Acceptance criteria

| Area | Minimum target |
|---|---:|
| Included documents with confirmed AD identity | 100% |
| Operational documents with verified lifecycle state | 100% |
| Gold records passing schema validation | 100% |
| Step 3 gold releases passing strict schema, evidence, and reusable release gates | 100% |
| Published Step 3 releases passing exact Drive readback | 100% |
| Extraction schema-valid output | >= 98% |
| Core-field extraction macro F1 | >= 0.85 |
| Compliance-unit tuple F1 | >= 0.80 |
| Classification macro F1 | >= 0.85 |
| Retrieval Recall@5 | >= 0.90 |
| Retrieval MRR | >= 0.80 |
| Latest-version selection accuracy | >= 0.98 |
| Citation correctness | >= 0.95 |
| Evidence faithfulness | >= 0.95 |
| Unsupported-claim rate | <= 0.05 |

These are planned success thresholds. The final report must present the actual measured results even when a target is missed.

For Step 3, validator success alone is insufficient: the release must also contain explicit independent approval provenance and pass versioned publication plus Drive readback.

---

# 9. Exact schedule: 13 July-30 September 2026

The plan begins Monday, 13 July 2026 and ends Wednesday, 30 September 2026. The first 11 weeks contain the research and implementation work; the final three days are reserved for submission checks and the demonstration package.

**Week 1 | 13-19 July**

- Work: Finalize the literature review, project scope, research questions, and methodology; prepare and pilot 6.1.
- Output: Approved scope, methodology draft, and pilot manifest.

**Week 2 | 20-26 July**

- Work: Run 6.1 on all PDFs; inspect corpus statistics, duplicates, revisions, corrections, OCR flags, and supersedure candidates.
- Output: Full initial manifest and audit reports.

**Week 3 | 27 July-2 August**

- Work: Continue 6.2 corpus review; finalize the versioned Step 2 schema and `PDF_TO_GOLD_FRAMEWORK`; preserve or import the validated 30-record pilot release evidence; prepare and pre-human validate the separate 20-record Step 3 batch.
- Output: Corpus-review evidence, schema/framework v1, preserved 30-record release audit trail, and source-verified 20-record review batch.

**Week 4 | 3-9 August**

- Work: Independently review the 20-record batch only in `human_review_working/`; strictly validate and publish the approved 20 as a new versioned release; create a separate combined 50-record release; draft the first 50 questions and implement section reconstruction in parallel.
- Output: Versioned 20-record and combined 50-record release evidence, QA draft v1, and reviewed chunks v1.

**Week 5 | 10-16 August**

- Work: Select and review the remaining 50 records required for the fixed core through versioned Step 3 batches; draft questions 51-100; perform second review and adjudication; freeze family-level splits; begin the rule-based extraction baseline.
- Output: Core gold dataset v1, 100-question draft, frozen splits, and baseline predictions.

**Week 6 | 17-23 August**

- Work: Draft questions 101-150 and 30 human reference summaries; implement and compare deterministic, zero-shot, and few-shot extraction; add validators, evidence spans, action classification, and structured summary templates.
- Output: Complete benchmark drafts, selected extraction/classification pipeline, and summaries v1.

**Week 7 | 24-30 August**

- Work: Evidence-check and lock all 150 QA questions and 30 reference summaries; implement BM25, dense-only, and flat-chunk retrieval baselines. Start optional AD expansion only if the 100-AD core set has passed every completion gate.
- Output: Locked QA/summary benchmarks and baseline retrieval report.

**Week 8 | 31 August-6 September**

- Work: Implement metadata filtering, hybrid retrieval, reciprocal-rank fusion, reranking, and the mandatory version-selection policy.
- Output: Version-aware retriever v1.

**Week 9 | 7-13 September**

- Work: Implement grounded answer generation, page citations, lifecycle warnings, confidence checks, and abstention; connect the end-to-end prototype.
- Output: End-to-end assistant v1.

**Week 10 | 14-20 September**

- Work: Run extraction, classification, summarization, retrieval, version-selection, QA, citation, and faithfulness evaluation.
- Output: Complete metric tables and prediction archives.

**Week 11 | 21-27 September**

- Work: Run essential ablations and error analysis; finish the UI, tests, documentation, thesis chapters, and supervisor corrections.
- Output: Release candidate, ablation/error report, and thesis draft.

**Final submission window | 28-30 September**

- Work: Freeze code and data; run reproducibility and submission checks; finalize the thesis, presentation, and demonstration.
- Output: Final submission package.

## Weekly control routine

- Monday: define measurable weekly deliverable.
- Wednesday: run a quality check on a small sample and record blockers.
- Friday: commit code/configuration, archive outputs, and update the technical diary.
- Supervisor meeting: show artifacts and errors, not only verbal progress.
- Never change the locked test set after Week 7.
- For every Step 3 release, archive its frozen selection, source/page/annotation hashes, reviewer provenance, validation commands and report, release notes, Drive folder identifier, and readback date.

---

# 10. Recommended project structure

```text
Capstone_AD_Project/
├── corpus_raw/                  # Immutable source PDFs
├── corpus_ocr/                  # OCR derivatives, never replacements
├── metadata/                    # Manifest, overrides, lifecycle links
├── step2_ad_schema/             # Versioned schema, guidance, vocabularies, validators
├── step3_pilot/                 # Frozen 30-record pilot and audit trail
├── step3_extension_20_v1/       # Separate 20-record batch and review surfaces
├── dataset_framework/           # Batch checklist, registry, reusable release gate
├── gold_releases/               # Immutable versioned releases only
│   └── <release-id>/
│       ├── selection.json
│       ├── annotations/
│       ├── validation/
│       ├── annotation_manifest.csv
│       ├── source_manifest.csv
│       └── RELEASE_NOTES.md
├── annotations/                 # QA, summaries, agreement, and benchmark lock artifacts
├── data_processed/
│   ├── historical/
│   ├── operational/
│   ├── sections/
│   └── chunks/
├── src/
│   ├── corpus/
│   ├── extraction/
│   ├── classification/
│   ├── summarization/
│   ├── retrieval/
│   ├── generation/
│   └── evaluation/
├── configs/                     # Frozen experiment configurations
├── prompts/                     # Versioned prompt templates
├── experiments/                 # Metrics, logs, predictions
├── app/                         # Research prototype UI/API
├── tests/
├── reports/
├── docs/
│   └── PDF_TO_GOLD_FRAMEWORK.md
└── README.md
```

## Reproducibility rules

- Use Git for code, prompts, schema, and small metadata files.
- Keep raw PDFs read-only.
- Assign stable IDs and retain hashes.
- Store every model name/revision, prompt version, seed, threshold, and environment file.
- Use deterministic seed `42` where supported.
- Separate generated predictions from manually verified labels.
- Do not overwrite experiment outputs; create versioned run directories.
- Record API cost and latency when hosted models are used.
- Keep frozen Step 3 selections, sources, and `human_review_queue/` read-only.
- Edit Step 3 annotations only in the batch `human_review_working/` folder.
- Never infer human approval from automated extraction or validator success.
- Publish only approved records in a new versioned release and preserve every earlier release.
- Record the exact release validator report, Drive folder identifier, and Drive readback date.
- Version schema/guideline changes, update the changelog, regression-validate existing gold, and record the migration decision.

---

# 11. Risks and mitigations

- **OCR errors in older PDFs:** Wrong identifiers or compliance numbers. Mitigate with page-level visual verification, confidence flags, and retention of the original page image.
- **Revision-family leakage:** Inflated evaluation. Split only by `base_ad_number`.
- **Correction mistaken for revision:** Incorrect latest-version logic. Represent correction state separately and manually verify lifecycle order.
- **Complex action/time relationships:** Incorrect compliance units. Use repeatable units, evidence spans, and explicit adjudication rules.
- **Machine output mistaken for human-approved gold:** Invalid benchmark labels. Keep machine-assisted states false/non-approved, require explicit independent approval provenance, and fail closed when approval is missing.
- **Frozen queue or prior release overwritten:** Loss of auditability. Edit only working copies and publish every approved batch or combination under a new release version.
- **Wrong attachment or incomplete PDF review:** Evidence may be structurally valid but substantively wrong. Freeze canonical source identity and visually inspect every page, including tables, appendices, scans, and multi-column layouts.
- **Local validation mistaken for publication:** Incomplete release claim. Require reusable strict release validation followed by exact Drive readback of files and the final report.
- **Excessive annotation workload:** Schedule delay. Treat 100 ADs, 150 questions, and 30 summaries as the fixed core. Attempt the 200-AD/50-summary stretch only after core validation, and accept pre-annotation only with human verification.
- **Rare classification labels:** Unstable macro F1. Merge labels that cannot be supported, report per-label support, and use class weighting where justified.
- **LLM hallucination:** Unsupported or unsafe answers. Use evidence-only prompts, validators, citation checks, and abstention.
- **Historical text retrieved as current:** Outdated requirements. Use the operational index and mandatory lifecycle filtering.
- **Limited aviation-domain review:** Ground-truth uncertainty. Flag ambiguity, request targeted supervisor review, and report reviewer limitations.
- **API or compute limits:** Incomplete experiments. Use small-model baselines, caching, a fixed development sample, and cost tracking.

---

# 12. Supervisor decision checkpoints

Request explicit supervisor approval at these points:

1. **After 6.2:** final inclusion/exclusion rules and canonical corpus counts.
2. **Before publishing the separate 20-record Step 3 batch:** confirm complete independent review, explicit approval provenance, strict release validation, and the versioned release package.
3. **Before publishing the combined 50-record release:** confirm that it equals the preserved 30 plus approved 20 and does not mutate either earlier release.
4. **Before completing the 100-record core:** approve the remaining sampling strategy, 60/20/20 family-level split, 150-question design, 30-summary design, and optional 200-record extension rule.
5. **After baseline experiments:** final extraction/embedding/reranker choices.
6. **Before locked testing:** metrics, acceptance thresholds, and test IDs.
7. **After evaluation:** interpretation of missed targets and thesis claims.

No major schema, split, or evaluation change should be introduced after locked testing without documenting it as a new experiment.

---

# 13. Immediate next actions

Complete these actions in order:

1. Preserve or import the exact validated 30-record pilot into the versioned `gold_releases/` contract with its selection, approved annotations, manifests, final report, release notes, Drive folder identifier, and readback date. Do not alter the prior release.
2. Review and correct each separate 20-record candidate only in `step3_extension_20_v1/human_review_working/`.
3. Obtain explicit independent approval before setting manual, approved, human-confirmed, or gold state.
4. Run strict Step 2 schema/semantic validation and exact evidence validation against the frozen 20-record sources.
5. Run `dataset_framework/validate_gold_release.py` against the exact 20-record selection, source PDFs, and page-text cache; require zero errors from all five gates.
6. Publish the approved 20-record batch as a new versioned release and verify it by Drive readback.
7. Create and validate a separate combined 50-record release containing exactly the preserved 30 plus approved 20; keep the earlier releases unchanged.
8. Select and review the remaining records required for the fixed 100-record core, then freeze the 60/20/20 family-level split.
9. In parallel, complete Phase 6.2 review of `processing_and_metadata_review.csv`, `duplicate_review.csv`, `version_chains.csv`, `near_duplicate_candidates.csv`, and `supersedure_links.csv`.
10. Record corpus-manifest corrections only in `manual_overrides.csv` and reproducibly generate the canonical historical and operational views.

Do not start the final vector index until the relevant PDF sources, lifecycle decisions, Step 3 gold releases, and canonical operational view have passed their required gates.

---

# 14. Proposal-ready methodology summary

This research will construct a controlled corpus of Airbus S.A.S. Airworthiness Directives issued by EASA and develop a version-aware AI framework for maintenance-information automation. The method first inventories every PDF, detects exact and near duplicates, distinguishes original issues, revisions and corrections, verifies supersedure relationships, and produces separate historical and latest-version operational corpus views. A domain-specific schema then represents each directive as evidence-linked compliance units connecting applicability conditions, required actions, initial compliance thresholds, repetitive intervals, terminating actions, and referenced publications. Step 3 converts selected canonical PDFs into gold only through frozen source identity, immutable review queues, editable working copies, explicit independent human approval, strict schema/evidence/release validation, versioned publication, and exact Drive readback. The 30-record pilot and combined 50-record release are preserved checkpoints toward the fixed 100-record family-split benchmark. That benchmark will support the development and evaluation of deterministic and language-model-based extraction, multi-label action classification, and evidence-grounded summarization. For question answering, metadata filtering, BM25 retrieval, dense retrieval, reciprocal-rank fusion, and reranking will be combined with mandatory version-selection rules. The proposed system will be compared with flat, dense-only RAG and other baselines using extraction F1, retrieval Recall@K and MRR, latest-version accuracy, answer correctness, citation correctness, faithfulness, and unsupported-claim rate. The prototype will provide page-level evidence, warn about historical or superseded documents, and abstain when reliable evidence is unavailable.

---

# 15. Authoritative and methodological references

Project-internal authority for Step 3:

1. `AGENTS.md`
2. `docs/PDF_TO_GOLD_FRAMEWORK.md`
3. `step2_ad_schema/easa_airbus_ad_annotation.schema.json`
4. `step2_ad_schema/annotation_guidelines.md`
5. `step2_ad_schema/controlled_vocabularies.json`
6. `dataset_framework/BATCH_CHECKLIST.md`

External methodological references:

1. European Union Aviation Safety Agency. **Airworthiness Directives - Safety Publications.** <https://www.easa.europa.eu/en/domains/aircraft-products/airworthiness-directives-ad>
2. European Union Aviation Safety Agency. **Airworthiness Directives (ADs) - Frequently Asked Questions.** <https://www.easa.europa.eu/en/the-agency/faqs/airworthiness-directives-ads>
3. European Union Aviation Safety Agency. **EASA Safety Publications Tool.** <https://ad.easa.europa.eu/>
4. Lewis, P., et al. (2020). **Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.** NeurIPS 2020. <https://arxiv.org/abs/2005.11401>
5. Karpukhin, V., et al. (2020). **Dense Passage Retrieval for Open-Domain Question Answering.** EMNLP 2020. <https://aclanthology.org/2020.emnlp-main.550/>
6. Cormack, G. V., Clarke, C. L. A., and Buettcher, S. (2009). **Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods.** SIGIR 2009. <https://dl.acm.org/doi/10.1145/1571941.1572114>

The EASA sources define the regulatory document scope and lifecycle terminology. The retrieval references support the RAG, dense-retrieval, and rank-fusion components. The final literature review should additionally position the project against the aviation-document studies already recorded in the research tracking sheet.
