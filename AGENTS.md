# Agent Guide: Airbus EASA AD Capstone

This file is the primary handoff for any agent working in this repository. Read it before changing code, data rules, experiments, or documentation.

## 1. Project identity

- Student: Tun Wai Lin
- Project: Intelligent Engineering Document Automation for Aviation Maintenance
- Execution window: 13 July-30 September 2026
- Corpus: approximately 1,800 Airworthiness Directive PDFs
- Regulatory source: EASA Safety Publications Tool
- Approval holder in scope: Airbus S.A.S.
- Goal: build and evaluate a version-aware, evidence-grounded assistant that extracts, classifies, summarizes, and retrieves maintenance-compliance information from ADs.

The research prototype supports engineering review. It does not determine legal compliance, authorize maintenance, or replace licensed engineering judgment.

## 2. Research contribution

Do not claim that RAG, LLM extraction, or aviation question answering is individually novel. The defensible contribution is their integration:

> Corpus governance + AD lifecycle modelling + structured compliance extraction + version-aware hybrid retrieval + evidence-level traceability + human-validated evaluation.

The system must treat an AD as a version-controlled, safety-critical regulatory document, not as an independent generic PDF.

## 3. Fixed scope

Included:

- Final EU-issued EASA ADs for Airbus S.A.S.
- Original, emergency, revised, corrected, and superseded historical versions.
- English PDF content and EASA metadata.
- Extraction, classification, summarization, retrieval, question answering, citations, and version selection.

Excluded unless the user and supervisor explicitly change scope:

- Proposed ADs and Safety Information Bulletins.
- Foreign-issued ADs.
- Airbus Helicopters, Airbus Canada, engines, and approval holders other than Airbus S.A.S.
- Service Bulletins as primary indexed documents; extract their identifiers only.
- Aircraft-specific compliance determination, work-order generation, or release-to-service authorization.

## 4. Non-negotiable data rules

1. Treat `corpus_raw/` as immutable. Never delete, rename, overwrite, or edit a source PDF.
2. Keep OCR files as derivatives under `corpus_ocr/`.
3. Use one manifest row per physical PDF and stable `file_instance_id` values.
4. Record corpus-manifest corrections in `manual_overrides.csv`; do not hand-edit a generated manifest.
5. Do not automatically delete near duplicates, revisions, corrections, emergency issues, or same-version conflicts.
6. Maintain both:
   - a historical view containing verified lifecycle versions; and
   - an operational view containing the latest verified applicable publication by default.
7. Split datasets by `base_ad_number`. All versions in one AD family must remain in the same partition.
8. Keep gold labels separate from generated predictions.
9. Never silently combine requirements from different AD versions.
10. Answers must cite AD number, version, page, and evidence section or span. Abstain when evidence is missing or conflicting.

For Step 3 annotations, `docs/PDF_TO_GOLD_FRAMEWORK.md` is authoritative:

1. Treat every frozen selection and `human_review_queue/` as read-only.
2. Freeze canonical PDF identity and hashes before annotation; never substitute a similar or superseded attachment.
3. Review the complete canonical PDF, including tables, appendices, footnotes, diagrams, scans, and multi-column text.
4. Trace every populated safety-relevant value to page-grounded evidence.
5. Make annotation corrections only in `human_review_working/`.
6. Automated extraction and validation never constitute human approval.
7. Do not set manual, approved, human-confirmed, or gold state without explicit independent human approval.
8. Move through the framework lifecycle without skipping a gate:
   `selected → source_verified → machine_first_pass → human_review_pending → human_review_in_progress → human_approved → gold_validated → gold_published`.
9. Publish approved records only in a new versioned gold release; never overwrite an earlier release.
10. A release is complete only after strict release validation and Drive readback of the exact release files and report.

## 5. Central research object

The main extracted object is a compliance unit linking:

```text
applicability/condition
  -> required action and method
  -> initial compliance threshold
  -> repetitive interval
  -> terminating action or exception
  -> referenced publication
  -> page-level evidence
```

Core fields include AD identity and lifecycle, dates, affected aircraft or part, ATA chapter, unsafe condition, consequence, required action, compliance timing, repeat interval, terminating action, referenced publications, and provenance.

## 6. Planned benchmark

- 100 manually annotated ADs as the fixed core gold set.
- Optional expansion to 200 annotated ADs only after the 100-AD core passes validation.
- 150 locked QA questions.
- 30 human reference summaries, with an optional expansion to 50.
- Test benchmark locks in Week 7 and must not be tuned after inspection.
- Seed: `42` where supported.

The original 20-document core test partition remains frozen even if the gold set expands. Any extension test partition must be locked separately, and its results must be reported separately before pooling.

Step 3 release sizes are delivery checkpoints, not changes to this benchmark:

- the frozen 30-record pilot is the first reviewed release;
- the 20-record Step 3 batch is reviewed and released separately;
- a combined 50-record release must be a new version that preserves the 30-record release; and
- the 30- and 50-record releases contribute toward the fixed 100-AD core. They are not the optional 200-record stretch.

Primary system comparison:

- E0: flat chunks + dense-only generic RAG.
- E4: section-aware chunks + hybrid retrieval + reranking + lifecycle filtering + structured records and evidence.

Planned thresholds are documented in `docs/PROJECT_PLAN.md`. Always report actual results even if a target is missed.

## 7. Current repository state

This repository contains the Phase 6.1 corpus audit and the current Step 3 annotation workflow. It includes:

- a full 1,809-row manifest snapshot and corpus audit reports;
- the versioned Step 2 annotation schema and validators;
- a frozen 30-record Step 3 pilot with approved working records and passing strict/evidence validation;
- a frozen 20-record Step 3 batch whose machine-assisted candidates pass pre-human validation but remain non-gold;
- the reusable `dataset_framework/validate_gold_release.py` release gate; and
- automated Step 2 and Step 3 tests.

Important distinction: a successful manifest run does not prove lifecycle review or canonical-corpus completion, and approved working JSON is not by itself a published gold release. Check `docs/PROJECT_STATUS.md`, the exact batch artifacts, validation reports, and Drive readback evidence before making a completion claim.

## 8. Working protocol

Use this authority order:

1. the user's current request;
2. this `AGENTS.md`;
3. `docs/PDF_TO_GOLD_FRAMEWORK.md` for all Step 3 annotation batches and releases;
4. the versioned Step 2 schema, annotation guidelines, and controlled vocabularies;
5. `docs/DECISIONS.md`;
6. `docs/BENCHMARK_DESIGN.md`;
7. `docs/PROJECT_PLAN.md`;
8. `docs/PROJECT_STATUS.md`;
9. README and implementation details.

Before work:

1. Read `docs/PROJECT_STATUS.md`.
2. For Step 3, read `docs/PDF_TO_GOLD_FRAMEWORK.md` and `dataset_framework/BATCH_CHECKLIST.md`.
3. Inspect the relevant code, inputs, and existing outputs.
4. Distinguish confirmed artifacts from planned work.

During work:

- Preserve unrelated user changes.
- Make pipeline stages reproducible and configuration-driven.
- Retain model name/revision, prompt version, thresholds, seed, latency, and cost where applicable.
- Store experiment outputs in versioned run directories; do not overwrite prior runs.
- Keep Step 3 selection, queue, working, staging, and versioned release artifacts separate.
- Use `step3_pilot/validate_step3_pilot.py` only for the frozen 30-record pilot.
- Use `dataset_framework/validate_gold_release.py` for any new batch or combined release.
- Version any Step 2 schema or guideline change, update its changelog, regression-validate existing gold, and record an explicit migration decision.
- Add tests for parsing rules, lifecycle ordering, extraction validation, and version selection.
- Prefer small, auditable changes that can be verified on a representative sample before a full-corpus run.

After material work:

1. Run the relevant tests and record the exact command and result.
2. Update `docs/PROJECT_STATUS.md` with evidence, next action, and blockers.
3. Add a dated entry to `docs/DECISIONS.md` if a stable project decision changed.
4. For a Step 3 release, save the frozen selection, source and annotation hashes, reviewer provenance, validation report, release notes, Drive location, and readback date.
5. Do not mark a phase or release complete until its completion gate is satisfied.

## 9. Common commands

Install and test:

```bash
python -m pip install -e ".[dev]"
pytest -q
```

Build the manifest:

```bash
ad-corpus-manifest build \
  --input "/path/to/corpus_raw" \
  --output "/path/to/metadata"
```

Quick first pass:

```bash
ad-corpus-manifest build \
  --input "/path/to/corpus_raw" \
  --output "/path/to/metadata" \
  --skip-near-duplicates
```

Validate a Step 3 batch after explicit human approval:

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

## 10. Immediate priority

The next evidence-based sequence is:

1. Preserve the validated 30-record Step 3 pilot and its audit trail as an immutable versioned release.
2. Complete explicit independent human review of the 20-record Step 3 batch only in `human_review_working/`.
3. Strictly validate and publish the approved 20-record batch as its own versioned release with Drive readback.
4. Create a separate combined 50-record release without changing the earlier 30-record release.
5. Continue from 50 to the fixed 100-AD core, freeze the family-level 60/20/20 split, and complete the QA and summary benchmarks.
6. In parallel, complete Phase 6.2 lifecycle review and canonical historical/operational corpus generation.

Do not begin the final vector index using unvalidated PDFs.
