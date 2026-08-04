# Project Status

Last updated: 4 August 2026

This file records only the active v3.1 project state.

## Current position

- Frozen snapshot: **1,809 physical PDF records / 1,808 base AD families**.
- Nominal development extraction: **1,804 PDFs** after reserving five unseen PDFs.
- Stated research scope: EU-issued EASA ADs whose Design/Type Approval Holder is Airbus S.A.S., accepting legacy Airbus/Airbus Industrie naming.
- Methodology: **section-complete deterministic local extraction + original-PDF page-aware RAG**.
- Content schema: **2.1.0**.
- Active local parser: **v2.1.6**.
- Extraction evaluator: **content-eval-v3.1.5**.
- Corpus scope audit: **corpus-scope-audit-v1.2**.
- Hosted semantic extraction: **not used**.
- Immutable audit source: `gold_releases/easa_airbus_ad_gold_v2/` with 50 validated records.
- Nominal extraction split: 30 development / 20 test, seed 42.
- QA benchmark: `evaluation_sets/easa_airbus_ad_qa_50_v2/`, 50 questions.
- v2.1.5 development run exists locally and is retained as development evidence but is **not final/canonical**.
- Next run target: `data_processed/runs/local-content-development-1804-v2.1.6/`.
- Next canonical target: `data_processed/canonical_content_v2.1.6/` after development freeze and clean test evaluation.

## Development-reference audit result

The nominal 30 development references were audited against the immutable release:

- critical issues: **0**;
- approved/projection-locked eligible references: yes;
- holder-scope exclusions: **2**;
  - `2024-0095` — Airbus Defence and Space S.A.;
  - `2026-0079` — Lufthansa Technik AG;
- scored primary development records: **28**.

These exclusions remain immutable audit artifacts but are not primary Airbus S.A.S. development scores. The document-level evidence-quote containment check remains auxiliary; page hashes and approved evidence provenance are the stronger anchors.

## v2.1.5 development evaluation result

Evaluator v3.1.5 on the regenerated v2.1.5 run showed:

- prediction coverage: **1.000**;
- schema validity: **1.000**;
- stable metadata macro F1: **0.9671**;
- applicability-model F1: **0.9565**;
- reference-number F1: **0.8065**;
- superseded-AD-number F1: **0.9000**;
- raw difficult-section presence: **1.000** for Definitions, Reason, Required Actions/Compliance, Ref. Publications, and Remarks;
- raw-section source containment: **130/130 = 1.000**;
- detected raw-section page-furniture contamination: **0** across all five difficult-section types.

This means the section-complete raw-text layer is now behaving as intended on the scored development set.

## Why v2.1.5 is not the final freeze

The same development report/source review exposed narrow remaining deterministic catalogue/scope defects:

- `2019-0183`, `2020-0016`, and `2020-0092` use `Design Approval Holder’s Name::` with a doubled colon and were missed by v2.1.5;
- legacy records such as `2006-0122`, `2006-0174`, and `2007-0162` use `Type Approval Holder’s Name` plus `Type/Model designations:`;
- `2023-0093R1` prints consecutive ATA 32 and ATA 92 subject blocks, while v2.1.5 retained only ATA 92;
- the same `2023-0093R1` wording says the current AD revises an earlier issue which itself superseded another AD, and v2.1.5 converted that chain into false direct supersedure numbers;
- some A300 applicability variants are printed with extra hyphens such as `A300-B4-601`;
- the full-corpus scope audit still contained unresolved parser-derived holder strings.

No clean locked-test content was opened to derive these fixes.

## v2.1.5 corpus-scope audit result

The v2.1.5 full-corpus scope audit reported:

- total records: **1,804**;
- eligible: **1,765**;
- excluded: **17**;
- unknown: **22**.

These counts are diagnostic, not final. Review showed that several unknowns are merely unrecognized Airbus aliases, several contain adjacent model/applicability leakage, and multiple missing-holder cases have an explicit Airbus approval-holder line in the source PDF. Therefore `1765` is **not** the final Airbus-only corpus count.

The 17 confirmed external/mixed-holder records remain preserved as physical/source content records but are excluded from the strict Airbus-only operational view. Any remaining `unknown` after v2.1.6 must be individually resolved before the scope-approved operational count is frozen.

## Parser v2.1.6 changes

v2.1.6 is a development-only hardening layer over v2.1.5. It adds:

- doubled-colon DAH heading normalization;
- legacy `Type Approval Holder` and plural multi-holder heading normalization;
- legacy `Type/Model designations:` normalization;
- consecutive multi-ATA subject recovery;
- safe handling of revision chains so `This AD revises X, which superseded Y` does not create false direct supersedure edges;
- flexible A300 variant extraction with optional extra hyphens; and
- removal of obvious A300 ATA/reference fragments from structured applicability models.

The active extraction and permanent-ingestion paths now import `local_extractor_v216.py`, while v2.1.5 remains preserved as the underlying frozen parser implementation for reproducibility.

## Scope-policy v1.2

`full_corpus_pipeline/scope_policy.py` defines the strict operational scope:

- accepted Airbus S.A.S./legacy Airbus aliases → eligible;
- confirmed external or mixed approval holders → excluded from the strict Airbus-only operational view only;
- missing, malformed, or unfamiliar holder text → unknown pending review.

Physical source records are never deleted to manufacture a cleaner corpus count.

A multi-holder record such as `2011-0043` is not forced into Airbus-only scope simply because Airbus appears among several approval holders.

## Test leakage disclosure

- `2024-0038` belongs to the nominal test split.
- Its source PDF was previously used to diagnose parser defects.
- It remains automatically excluded from clean extraction-test scoring.
- The nominal split itself remains immutable for auditability.

## Immediate next actions

1. Pull v2.1.6 and run the full unit-test suite.
2. Regenerate all nominal 1,804 development records into `local-content-development-1804-v2.1.6`.
3. Rerun the 30-record development-reference audit.
4. Rerun the 1,804-record scope audit using audit v1.2.
5. Run evaluator v3.1.5 on the v2.1.6 development records.
6. Review every remaining scope `unknown`; do not reinterpret confirmed exclusions as parser failures.
7. Perform fresh representative PDF spot checks.
8. Freeze parser/evaluator behavior if the development gate passes.
9. Run the clean locked test split once and do not tune after viewing its results.
10. Promote `canonical_content_v2.1.6/` only if the clean extraction and scope gates pass.
11. Generate page-preserving PDF text, build E0/E4, and run retrieval/QA evaluation.
12. Test and permanently ingest the five unseen PDFs without retraining.

## Promotion gate

Do not promote v2.1.6 until all of these hold:

- 1,804 requested / 1,804 successful / zero extraction failures;
- development prediction coverage and schema validity are 100%;
- raw difficult sections remain source-complete, source-contained, and free of material page furniture;
- doubled-colon/legacy holder formats are recovered;
- multi-ATA subject coverage is complete on development evidence;
- no false direct supersedure edges remain from revision chains;
- every scope `unknown` is resolved or explicitly documented before freezing the operational subset count;
- representative PDF spot checks pass; and
- clean test evaluation is run only after development freeze.

## Reporting boundary

Do not claim:

- that v2.1.4 or v2.1.5 scope counts are final;
- that all 1,809 frozen records are confirmed Airbus S.A.S. approval-holder records before scope review is complete;
- that schema validation alone proves semantic correctness;
- that all records contain normalized compliance logic;
- that the nominal test split remained fully unseen after the disclosed `2024-0038` leak; or
- that the prototype determines aircraft-specific compliance.

The original PDF passage remains authoritative for complex compliance interpretation and QA citations.
