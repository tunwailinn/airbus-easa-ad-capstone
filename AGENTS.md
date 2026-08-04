# Agent Guide: Airbus EASA AD Capstone v3.1

Read this before changing code, data rules, experiments, or documentation.

## Project boundary

- Frozen snapshot: 1,809 physical Airbus-related EASA AD PDFs / 1,808 base AD families.
- Stated research scope: EU-issued EASA ADs whose Design/Type Approval Holder is Airbus S.A.S., accepting legacy Airbus/Airbus Industrie naming.
- Nominal development extraction: 1,804 PDFs after reserving five unseen PDFs.
- The frozen snapshot is not assumed to be perfectly scope-clean; holder-scope audits must be run before canonical scope claims/counts are frozen.
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

1. Treat source PDFs as immutable.
2. Keep one generated content record per physical PDF during extraction; scope eligibility is a governance/filtering decision, not a reason to silently rewrite the source inventory.
3. Never merge passages or requirements from different PDF versions.
4. Keep lifecycle/latest-selection state outside content JSON.
5. Keep generated predictions separate from the immutable 50-record audit source.
6. Do not add evidence spans, confidence, review status, model metadata, or machine-status labels to content records.
7. Preserve Applicability, Definitions, Reason, Requirements/Compliance, reference wording, and Remarks when printed.
8. Do not machine-normalize difficult compliance conditions, intervals, exceptions, or terminating logic across the full corpus.
9. RAG answers must cite AD number, source PDF, page, and section when available.
10. Abstain when retrieved support is incomplete or conflicting.
11. Temporary upload and permanent ingestion do not retrain models.
12. Printed PDF metadata is authoritative over stale manifest metadata when the parser can read it directly.
13. Do not promote a generated corpus after a parser-version change until it has been regenerated and re-evaluated.
14. Primary extraction metrics enforce Airbus S.A.S. holder scope from reviewed gold metadata and report exclusions explicitly.
15. Machine-extracted malformed/missing holder values are `unknown`, not automatic out-of-scope exclusions.
16. Do not use new clean locked-test content to tune extraction. Preserve the nominal split and disclose known leakage/exclusions rather than replacing members.

## Active versions and artifacts

- Content schema: `2.1.0`.
- Local deterministic parser: **`content-local-v2.1.5`**.
- Extraction evaluator: **`content-eval-v3.1.5`**.
- v2.1.4 generated run: `data_processed/runs/local-content-development-1804-v2.1.4/` — **stale, do not promote**.
- Next run: `data_processed/runs/local-content-development-1804-v2.1.5/`.
- Next canonical target: `data_processed/canonical_content_v2.1.5/`.
- Immutable audit source: `gold_releases/easa_airbus_ad_gold_v2/`.
- Nominal content benchmark: `evaluation_sets/easa_airbus_ad_content_gold_50_v2/`, 30 development / 20 test.
- Confirmed development scope exclusions:
  - `2024-0095`: Airbus Defence and Space S.A.;
  - `2026-0079`: Lufthansa Technik AG.
- Known test leakage: `2024-0038` was used in earlier parser diagnosis and must be excluded from clean extraction-test scoring.
- QA benchmark: `evaluation_sets/easa_airbus_ad_qa_50_v2/`.
- Unseen set: `evaluation_sets/unseen_incoming_5_v1/`.
- Active source reference files:
  - `step3_pilot/source_metadata/corpus_manifest.parquet`
  - `step3_pilot/source_metadata/corpus_extracted_text.parquet`

## Parser v2.1.5 rules

- Strip modern and legacy repeated page furniture, including `EASA Form N Page x/y`, `Page x/y`, TE.CAP/footer lines, repeated AD headers, and uppercase status watermarks.
- Preserve ordinary regulatory prose containing lowercase words such as `superseded`.
- Recognize wrapped legacy headings such as `Required Action(s) / and Compliance / Time(s):`.
- Do not treat ordinary prose beginning with `compliance`, `contact`, or similar words as a new section unless it is an actual heading.
- Preserve sections across page boundaries.
- Keep DAH, Type/Model, Foreign AD, revision, supersedure, and other header fields separate.
- Never treat Type/Model/applicability prose as a valid DAH value.
- Legacy Airbus documents lacking an explicit DAH-name field may use a conservative Airbus `Manufacturer(s)` fallback only when the document is not an STC/modification case.
- Use printed `Issued:` / legacy `Date:` before manifest issue-date fallback.
- Preserve the complete subject around ATA labels and support multi-ATA headings.
- Keep Remark contact lines and stop Remarks before later appendices/annexes.
- Extract publication identifiers only from the printed reference section; do not infer compliance semantics from them.

## Extraction evaluation rules

- Run `audit_development_reference.py` before tuning from the nominal development references.
- The current primary development score uses 28 eligible records; the nominal 30-member split remains immutable.
- Run `audit_corpus_scope.py` on every regenerated 1,804-record run before canonical promotion.
- Do not reuse the v2.1.4 `1729/59/16` scope result as a final count; many exclusions were malformed DAH parses.
- Raw-section expected presence is source-heading-driven when `corpus_extracted_text.parquet` is available.
- Raw difficult sections are evaluated for presence, source containment, and page-furniture/status contamination—not exact semantic-projection overlap.
- Detailed applicability models are primary; publication-header model expansion and family taxonomy are secondary diagnostics.
- Reference numbers and superseded AD numbers are scored separately.
- `legacy_projection_overlap` is diagnostic only.
- Never tune from clean test labels.

## Primary retrieval experiment

- E0: flat chunks + dense-only retrieval.
- E4: section-aware BM25 + dense retrieval + FAISS + RRF + reranking + metadata/lifecycle filtering.

## Working protocol

Authority order:

1. current user request;
2. this file;
3. `airbus_easa_ad_project_exact_plan.md`;
4. `docs/PROJECT_STATUS.md`;
5. `docs/DECISIONS.md`;
6. `docs/BENCHMARK_DESIGN.md`.

Before work, inspect current inputs/outputs and preserve unrelated changes. After material work, run relevant tests, update project status, and record stable methodology changes in `docs/DECISIONS.md`.

## Common commands

```bash
.venv/bin/python -m unittest discover -s full_corpus_pipeline/tests -v

.venv/bin/python -m full_corpus_pipeline.extract_corpus \
  --run-id local-content-development-1804-v2.1.5

.venv/bin/python -m full_corpus_pipeline.audit_development_reference \
  --output data_processed/runs/local-content-development-1804-v2.1.5/development_reference_audit.json

.venv/bin/python -m full_corpus_pipeline.audit_corpus_scope \
  data_processed/runs/local-content-development-1804-v2.1.5/records \
  --output data_processed/runs/local-content-development-1804-v2.1.5/corpus_scope_audit.json

.venv/bin/python -m full_corpus_pipeline.evaluate_extraction \
  data_processed/runs/local-content-development-1804-v2.1.5/records \
  --output data_processed/runs/local-content-development-1804-v2.1.5/evaluation_development_v3.1.5.json \
  --split development
```

## Immediate priority

1. Regenerate the nominal 1,804 development records with parser v2.1.5.
2. Run the development-reference audit, full scope audit, and evaluator v3.1.5.
3. Review only eligible development evidence for remaining genuine defects and perform fresh source-PDF spot checks.
4. Freeze parser/evaluator behavior.
5. Run the clean extraction test once with automatic scope/leakage disclosures.
6. Promote `canonical_content_v2.1.5/` only after validation.
7. Generate page-preserving text, build E0/E4, run retrieval/QA evaluation, then test permanent ingestion of the five unseen PDFs.
