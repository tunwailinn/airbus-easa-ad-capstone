# Project Status

Last updated: 4 August 2026

This file records only the active v3.1 project state.

## Current position

- Frozen snapshot: **1,809 physical PDF records / 1,808 base AD families**.
- Nominal development extraction: **1,804 PDFs** after reserving five unseen PDFs.
- Stated research scope: EU-issued EASA ADs whose Design/Type Approval Holder is Airbus S.A.S., accepting legacy Airbus/Airbus Industrie naming.
- Methodology: **section-complete deterministic local extraction + original-PDF page-aware RAG**.
- Content schema: **2.1.0**.
- Local parser: **v2.1.5**.
- Extraction evaluator: **content-eval-v3.1.5**.
- Hosted semantic extraction: **not used**.
- Immutable audit source: `gold_releases/easa_airbus_ad_gold_v2/` with 50 validated records.
- Nominal extraction split: 30 development / 20 test, seed 42.
- QA benchmark: `evaluation_sets/easa_airbus_ad_qa_50_v2/`, 50 questions.
- Previous v2.1.4 development run exists locally but is now **stale** and must not be promoted.
- Next run target: `data_processed/runs/local-content-development-1804-v2.1.5/`.
- Next canonical target: `data_processed/canonical_content_v2.1.5/` after validation.

## Development-reference audit result

The nominal 30 development references were audited against the immutable release:

- critical issues: **0**;
- approved/projection-locked eligible references: yes;
- current holder-scope exclusions: **2**;
  - `2024-0095` — Airbus Defence and Space S.A.;
  - `2026-0079` — Lufthansa Technik AG.

These two records remain immutable audit artifacts but are excluded from primary Airbus S.A.S. development scoring.

The document-level evidence-quote containment check is auxiliary only; page hashes and approved evidence provenance remain the stronger anchors.

## v2.1.4 development evaluation result

Evaluator v3.1.4 on the regenerated v2.1.4 run showed:

- prediction coverage: **1.000**;
- schema validity: **1.000**;
- stable metadata macro F1: **0.9449**;
- applicability-model F1: **0.9579**;
- reference-number F1: **0.5517**;
- superseded-AD-number F1: **0.8421**;
- raw-section source containment: **125/125 = 1.000** for sections that were extracted.

The same report exposed remaining development-only defects:

- legacy `EASA Form 110 Page x/y` / `Page x/y` furniture remained in preserved sections;
- multi-line `Required Action(s) / and Compliance / Time(s):` headings were missed in some old ADs;
- DAH extraction sometimes fell through into Type/Model text;
- older subject lines were truncated around ATA headings;
- France legacy TCDS identifiers were missed;
- deterministic reference-ID recall was low;
- some revision ADs did not recover direct original-issue supersedure.

## Why the v2.1.4 scope audit is not final

The v2.1.4 full-corpus scope audit reported `1729 eligible / 59 excluded / 16 unknown`, but many of the 59 `excluded` strings were obvious parser boundary failures such as:

- `type model designations airbus sas a310 ...`;
- long applicability/reason text captured as the holder;
- broad Airbus aircraft wording captured instead of an approval-holder value.

Therefore those counts must **not** be reported as the final in-scope corpus size.

Parser v2.1.5 fixes the underlying DAH behavior, and evaluator/scope classification now treats malformed holder text as `unknown` rather than silently declaring it out of scope. The v2.1.5 scope audit is the next authoritative diagnostic.

## Parser v2.1.5 changes

v2.1.5 is based only on disclosed development evidence and preserves the earlier v2.1.4 regressions. It adds:

- cleanup for legacy `EASA Form N Page x/y` and slash-style page counters;
- cleanup for page furniture embedded in semantic lines;
- wrapped legacy action/compliance heading recognition;
- strict DAH/Type-Model separation and conservative legacy Airbus manufacturer fallback;
- complete subject extraction before/after ATA labels and multi-ATA support;
- France TCDS recognition;
- avoidance of model false positives inside publication identifiers;
- broader deterministic reference-identifier extraction from the printed reference section; and
- recovery of direct `original issue of this AD superseded ...` lifecycle wording.

## Evaluator v3.1.5 changes

- Stable primary metadata no longer depends on expanded publication-header model lists when the PDF prints only broad family wording.
- Publication-model expansion and family labels remain secondary diagnostics.
- Raw-section expected presence is source-heading-driven whenever the document-text cache is available.
- `referenced_publications_text` is therefore source-scorable instead of being assigned a meaningless zero because the semantic gold projection has no equivalent raw field.
- Uppercase status watermarks are distinguished from legitimate lowercase supersedure prose.
- Malformed holder parser output is classified as `unknown`, not genuine scope exclusion.
- Known test leakage remains separately disclosed.

## Regression coverage

The current local regression suite covers:

- the original v2.1.4 printed-date, Foreign-AD, cross-page, page-furniture, and Remark-contact fixes;
- legacy development formats represented by ADs such as `2009-0141`, `2009-0171`, `2010-0164`, and `2011-0112`;
- DAH/Type-Model boundary behavior represented by `2008-0012`;
- richer reference/supersedure behavior represented by `2015-0135R3`; and
- evaluator source-heading/scope/contamination rules.

No new locked-test compliance content was used to tune v2.1.5.

## Test leakage disclosure

- `2024-0038` belongs to the nominal test split.
- Its source PDF was previously used to diagnose parser defects.
- It remains automatically excluded from clean extraction-test scoring.
- The nominal split itself remains immutable for auditability.

## Immediate next actions

1. Pull the v2.1.5 code and run the full unit-test suite.
2. Regenerate all nominal 1,804 development records into `local-content-development-1804-v2.1.5`.
3. Rerun the development-reference audit.
4. Rerun the 1,804-record corpus-scope audit.
5. Run evaluator v3.1.5 on the development split.
6. Review only eligible development evidence for any remaining genuine parser defect.
7. Perform fresh representative PDF spot checks.
8. Freeze parser/evaluator behavior.
9. Run the clean test split once.
10. Promote `canonical_content_v2.1.5/` only if the extraction and scope gates pass.
11. Generate page-preserving PDF text, build E0/E4, and run retrieval/QA evaluation.
12. Test and permanently ingest the five unseen PDFs without retraining.

## Promotion gate

Do not promote v2.1.5 until all of these hold:

- 1,804 requested / 1,804 successful / zero failures;
- development prediction coverage and schema validity are 100%;
- no unexpected printed Required Actions/Compliance sections are missing;
- repeated page furniture is no longer materially present in raw sections;
- DAH scope audit no longer mistakes Type/Model prose for genuine non-Airbus holders;
- remaining reference/lifecycle misses are understood and acceptable or fixed from development evidence;
- representative PDF spot checks pass; and
- clean test evaluation is run only after development freeze.

## Reporting boundary

Do not claim:

- that the old v2.1.4 `1729/59/16` scope counts are final;
- that all 1,809 frozen records are confirmed Airbus S.A.S. approval-holder records before the corrected scope audit is resolved;
- that schema validation alone proves semantic correctness;
- that all records contain normalized compliance logic;
- that the nominal test split remained fully unseen after the disclosed `2024-0038` leak; or
- that the prototype determines aircraft-specific compliance.

The original PDF passage remains authoritative for complex compliance interpretation and QA citations.
