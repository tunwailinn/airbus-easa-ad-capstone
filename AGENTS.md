# Agent Guide: Airbus EASA AD Capstone v3.1

Read this before changing code, data rules, experiments, or documentation.

## Project boundary

- Frozen snapshot: 1,809 physical Airbus-related EASA AD PDFs / 1,808 base AD families.
- Stated research scope: EU-issued EASA ADs whose Design/Type Approval Holder is Airbus S.A.S., accepting legacy Airbus/Airbus Industrie naming.
- Nominal development extraction: 1,804 PDFs after reserving five unseen PDFs.
- The frozen physical inventory is not assumed to be perfectly scope-clean; scope eligibility is an explicit operational/evaluation filter.
- Authoritative methodology: `airbus_easa_ad_project_exact_plan.md`.

## Architecture

```text
Section-complete deterministic content records
→ reliable metadata + raw difficult AD sections

Original PDF page chunks + RAG
→ compliance timing, conditions, exceptions, branches, cross-references, QA
```

Detailed compliance interpretation must use original PDF passages retrieved by RAG. Do not claim the extracted JSON contains fully normalized compliance logic.

## Non-negotiable rules

1. Source PDFs are immutable.
2. Keep one generated content record per physical PDF during extraction; scope eligibility is a governance/filtering decision, not a reason to delete or rewrite source records.
3. Never merge passages or requirements from different PDF versions.
4. Keep lifecycle/latest-selection state outside content JSON.
5. Keep generated predictions separate from the immutable 50-record audit source.
6. Do not add evidence spans, confidence, review status, model metadata, or machine-status labels to content records.
7. Preserve Applicability, Definitions, Reason, Requirements/Compliance, reference wording, and Remarks when printed.
8. Do not machine-normalize difficult compliance conditions, intervals, exceptions, or terminating logic across the full corpus.
9. RAG answers must cite AD number, source PDF, page, and section when available.
10. Abstain when retrieved support is incomplete or conflicting.
11. Temporary upload and permanent ingestion do not retrain models.
12. Printed PDF metadata is authoritative over stale manifest metadata when directly readable.
13. Do not promote after a parser-version change until the full run is regenerated and re-evaluated.
14. Malformed/missing machine-extracted holder values are `unknown`, never automatic exclusions.
15. Confirmed mixed/external approval-holder records remain in the physical inventory but are excluded from the strict Airbus-only operational view.
16. Do not use new clean locked-test content to tune extraction. Preserve the nominal split and disclose known leakage/exclusions rather than replacing members.

## Active versions and artifacts

- Content schema: `2.1.0`.
- Active local deterministic parser: **`content-local-v2.1.6`** via `local_extractor_v216.py`.
- Frozen underlying parser implementation: `content-local-v2.1.5` in `local_extractor.py`.
- Extraction evaluator: **`content-eval-v3.1.5`**.
- Corpus scope audit: **`corpus-scope-audit-v1.2`** using `scope_policy.py`.
- v2.1.5 run: `data_processed/runs/local-content-development-1804-v2.1.5/` — development evidence only, do not promote.
- Next run: `data_processed/runs/local-content-development-1804-v2.1.6/`.
- Next canonical target: `data_processed/canonical_content_v2.1.6/`.
- Immutable audit source: `gold_releases/easa_airbus_ad_gold_v2/`.
- Nominal content benchmark: `evaluation_sets/easa_airbus_ad_content_gold_50_v2/`, 30 development / 20 test.
- Primary development score currently has 28 eligible members; `2024-0095` and `2026-0079` are confirmed holder-scope exclusions.
- Known test leakage: `2024-0038` was used in earlier parser diagnosis and must be excluded from clean extraction-test scoring.
- QA benchmark: `evaluation_sets/easa_airbus_ad_qa_50_v2/`.
- Unseen set: `evaluation_sets/unseen_incoming_5_v1/`.
- Active source reference files:
  - `step3_pilot/source_metadata/corpus_manifest.parquet`
  - `step3_pilot/source_metadata/corpus_extracted_text.parquet`

## Development evidence already established

v2.1.5 development evaluation achieved:

- 100% prediction coverage and schema validity;
- stable metadata macro F1 about 0.967;
- reference-number F1 about 0.806;
- superseded-AD-number F1 0.900;
- 100% source-heading presence for all five raw difficult-section types;
- 130/130 raw-section source containment; and
- zero detected page-furniture contamination.

Therefore v2.1.6 must not redesign raw difficult-section extraction. It is a narrow catalogue/scope hardening pass only.

## Parser v2.1.6 rules

- Retain all v2.1.5 page-furniture, wrapped-heading, cross-page, printed-date, Remarks, and reference-section behavior.
- Normalize doubled-colon `Design Approval Holder’s Name::` headings before parsing.
- Normalize legacy `Type Approval Holder` and `Type Approval Holders names` labels to the common DAH label without changing holder values.
- Normalize legacy `Type/Model designations:` to `Type/Model designation(s):`.
- Preserve consecutive ATA subject blocks and every printed ATA code.
- Do not convert `This AD revises X, which superseded Y` into a direct current-AD supersedure edge.
- Recover A300 variants with optional extra hyphens, e.g. `A300-B4-601` → structured identifier `A300B4-601`.
- Do not interpret obvious A300 ATA/reference fragments such as `A300-24` as aircraft models.
- Do not add speculative publication-reference heuristics solely to raise recall; current high precision is more important than aggressive guessing.

## Scope-policy rules

- Accepted Airbus aliases → eligible.
- Confirmed external or mixed approval holders → excluded from the strict Airbus-only operational view only.
- Missing, malformed, or unclassified holders → unknown pending review.
- Multi-holder records such as `2011-0043` must not be forced into Airbus-only scope merely because Airbus is one listed holder.
- Unknowns must be resolved/documented before the final operational Airbus-only count is frozen.

## Evaluation rules

- Run `audit_development_reference.py` before using development scores.
- Run `audit_corpus_scope.py` on every regenerated 1,804-record run before canonical promotion.
- Raw-section expected presence is source-heading-driven when the document-text cache is available.
- Raw difficult sections are evaluated for presence, source containment, and page-furniture/status contamination—not exact semantic-projection overlap.
- Detailed applicability models are primary; publication-header expansion/family taxonomy are secondary diagnostics.
- Reference numbers and superseded AD numbers are scored separately.
- `legacy_projection_overlap` is diagnostic only.
- Never tune from clean test labels.

## Working protocol

Authority order:

1. current user request;
2. this file;
3. `airbus_easa_ad_project_exact_plan.md`;
4. `docs/PROJECT_STATUS.md`;
5. `docs/DECISIONS.md`;
6. `docs/BENCHMARK_DESIGN.md`.

After material changes, run relevant tests, update project status, and record stable methodology changes in `docs/DECISIONS.md`.

## Common commands

```bash
.venv/bin/python -m unittest discover -s full_corpus_pipeline/tests -v

.venv/bin/python -m full_corpus_pipeline.extract_corpus \
  --run-id local-content-development-1804-v2.1.6

.venv/bin/python -m full_corpus_pipeline.audit_development_reference \
  --output data_processed/runs/local-content-development-1804-v2.1.6/development_reference_audit.json

.venv/bin/python -m full_corpus_pipeline.audit_corpus_scope \
  data_processed/runs/local-content-development-1804-v2.1.6/records \
  --output data_processed/runs/local-content-development-1804-v2.1.6/corpus_scope_audit.json

.venv/bin/python -m full_corpus_pipeline.evaluate_extraction \
  data_processed/runs/local-content-development-1804-v2.1.6/records \
  --output data_processed/runs/local-content-development-1804-v2.1.6/evaluation_development_v3.1.5.json \
  --split development
```

## Immediate priority

1. Regenerate the nominal 1,804 development records with parser v2.1.6.
2. Run the development-reference audit, full scope audit v1.2, and evaluator v3.1.5.
3. Review all remaining scope unknowns and perform fresh development source-PDF spot checks.
4. Freeze parser/evaluator behavior if the development gate passes.
5. Run the clean extraction test once; do not tune after viewing it.
6. Promote `canonical_content_v2.1.6/` only after validation.
7. Generate page-preserving text, build E0/E4, run retrieval/QA evaluation, then test permanent ingestion of the five unseen PDFs.
