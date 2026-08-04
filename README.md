# Airbus EASA AD Extraction and RAG Capstone

Current methodology: **v3.1**.

This project processes a frozen snapshot of **1,809 Airbus-related EASA Airworthiness Directive PDFs**. Five PDFs are held out for unseen-document ingestion testing, leaving a nominal **1,804-PDF development extraction**. The stated research scope is EU-issued EASA ADs whose Design/Type Approval Holder is Airbus S.A.S., accepting legacy Airbus/Airbus Industrie naming; scope membership is audited rather than inferred from aircraft manufacturer alone.

The system has two layers:

```text
Section-complete deterministic content extraction
→ reliable metadata + complete raw difficult AD sections

Original-PDF page-aware RAG
→ compliance timing, conditions, exceptions, branches, citations, QA
```

Complex compliance semantics are intentionally interpreted from retrieved PDF passages at question time. Full-corpus extraction uses no hosted LLM.

## Active versions

- Content schema: `2.1.0`
- Local parser: **`content-local-v2.1.6`**
- Extraction evaluator: **`content-eval-v3.1.5`**
- Corpus scope audit: **`corpus-scope-audit-v1.2`**
- Immutable audit source: `gold_releases/easa_airbus_ad_gold_v2/`
- Active content benchmark: `easa_airbus_ad_content_gold_50_v2`
- Nominal split: 30 development / 20 test, seed 42
- QA benchmark: `easa_airbus_ad_qa_50_v2`
- Unseen ingestion set: 5 PDFs

The v2.1.5 development run is **successful development evidence but not final/canonical**:

```text
data_processed/runs/local-content-development-1804-v2.1.5/
```

Its development evaluation achieved 100% prediction coverage/schema validity and 100% source-contained, contamination-free preservation for all five raw difficult-section types across the scored development records. It nevertheless exposed narrow remaining catalogue/scope defects: doubled-colon DAH headings, legacy plural holder/model labels, consecutive multi-ATA subjects, a revision-chain supersedure false edge, and unresolved holder-scope records.

The next run/canonical targets are therefore:

```text
data_processed/runs/local-content-development-1804-v2.1.6/
data_processed/canonical_content_v2.1.6/
```

## Why v2.1.6 exists

v2.1.6 is a final development-only hardening layer over v2.1.5. It does **not** add semantic compliance normalization. It adds only source-format fixes supported by development evidence gathered before the locked test:

- `Design Approval Holder’s Name::` doubled-colon normalization;
- legacy `Type Approval Holder’s Name` and plural `Type Approval Holders names` labels;
- legacy `Type/Model designations:` spelling;
- preservation/classification of multi-holder records instead of forcing them into Airbus-only scope;
- recovery of consecutive ATA subject blocks such as ATA 32 followed by ATA 92;
- safer revision-chain handling so `This AD revises X, which superseded Y` is not converted into a false direct supersedure edge;
- flexible A300 model tokens printed with extra hyphens such as `A300-B4-601`; and
- removal of obvious A300 ATA/reference fragments such as `A300-24` from structured applicability models.

The strict operational scope policy now lives in `full_corpus_pipeline/scope_policy.py`:

- accepted Airbus S.A.S./legacy Airbus aliases → `eligible`;
- confirmed external or mixed approval holders → `excluded` from the strict Airbus-only operational view, while the physical PDF/content record remains preserved;
- missing, malformed or unfamiliar holder text → `unknown` and must be reviewed before the scope-approved canonical count is frozen.

## Run tests

```bash
.venv/bin/python -m unittest discover -s full_corpus_pipeline/tests -v
```

The v2.1.6 regression tests use development-derived/source-format evidence only. Do not add new locked-test content while tuning this parser.

## Regenerate the nominal 1,804 development records

```bash
.venv/bin/python -m full_corpus_pipeline.extract_corpus \
  --run-id local-content-development-1804-v2.1.6
```

Do not overwrite or relabel the v2.1.4/v2.1.5 runs.

## Audit the 30 nominal development references

```bash
.venv/bin/python -m full_corpus_pipeline.audit_development_reference \
  --output data_processed/runs/local-content-development-1804-v2.1.6/development_reference_audit.json
```

The immutable development audit has 30 nominal members and two known holder-scope exclusions:

- `2024-0095` — Airbus Defence and Space S.A.
- `2026-0079` — Lufthansa Technik AG

They remain in the immutable 50-record audit release but are not primary Airbus S.A.S. development scores.

## Audit all 1,804 generated records for holder scope

```bash
.venv/bin/python -m full_corpus_pipeline.audit_corpus_scope \
  data_processed/runs/local-content-development-1804-v2.1.6/records \
  --output data_processed/runs/local-content-development-1804-v2.1.6/corpus_scope_audit.json
```

Do not reuse earlier scope counts as final corpus counts. In particular, the v2.1.5 report (`1765 eligible / 17 excluded / 22 unknown`) contains known parser-format misses among the unknowns. Use only the regenerated v2.1.6 scope report for the next governance decision.

A confirmed mixed-holder document is not deleted; it remains in the immutable physical inventory but is excluded from the strict Airbus-only operational subset. Any remaining `unknown` record must be reviewed before freezing the scope-approved operational count.

## Run development extraction evaluation

```bash
.venv/bin/python -m full_corpus_pipeline.evaluate_extraction \
  data_processed/runs/local-content-development-1804-v2.1.6/records \
  --output data_processed/runs/local-content-development-1804-v2.1.6/evaluation_development_v3.1.5.json \
  --split development
```

Primary reporting separates:

- stable comparable metadata;
- secondary publication-model/family normalization;
- reference/lifecycle identifiers;
- source-heading-driven raw-section presence;
- source-text containment;
- page-furniture/status contamination;
- holder-scope exclusions; and
- known test-leakage exclusions.

`legacy_projection_overlap` remains diagnostic only and must not be reported as v3.1 extraction accuracy.

## Development freeze gate

Before touching the locked test split, verify all of the following on v2.1.6:

1. 1,804 requested records, 1,804 successful records, zero extraction failures.
2. 100% prediction coverage and schema validity on the scored development set.
3. Definitions, Reason, Required Actions/Compliance, Ref. Publications, and Remarks retain 100% source-heading presence where printed, source containment, and no material page-furniture contamination.
4. DAH parsing no longer misses the doubled-colon or legacy Type Approval Holder formats used by development evidence.
5. Consecutive multi-ATA subjects preserve every printed ATA chapter.
6. Revision wording does not create false direct supersedure edges.
7. Scope audit has no unresolved parser-garbage exclusions; every remaining `unknown` is individually reviewed before the scope-approved operational count is frozen.
8. Remaining reference-ID/model-taxonomy differences are documented as secondary limitations or fixed from development evidence only.
9. Representative source-PDF spot checks pass.

If a new genuine defect remains, do not inspect locked-test compliance labels to tune it.

## Final clean extraction evaluation

Only after development behavior is frozen:

```bash
.venv/bin/python -m full_corpus_pipeline.evaluate_extraction \
  data_processed/runs/local-content-development-1804-v2.1.6/records \
  --output data_processed/runs/local-content-development-1804-v2.1.6/evaluation_test_clean_v3.1.5.json \
  --split test
```

The nominal 20-record test split remains immutable. `2024-0038` is automatically excluded from clean test scoring because it was previously used to diagnose parser defects. Holder-scope exclusions are derived separately from reviewed gold metadata. Use the generated report's `record_count` as the actual clean test sample size.

Do not tune parser rules after inspecting clean locked-test results. Report failures as test results.

## Promote only after validation

```bash
.venv/bin/python -m full_corpus_pipeline.promote_extraction_run \
  data_processed/runs/local-content-development-1804-v2.1.6 \
  data_processed/canonical_content_v2.1.6 \
  --expected-count 1804
```

Promotion preserves one generated content record per nominal physical development PDF. The strict Airbus S.A.S.-only operational subset is a separate explicit scope filter/sidecar; never silently delete source records or rewrite the frozen inventory to manufacture a cleaner count.

## Next RAG stage

After extraction is frozen and promoted:

```bash
.venv/bin/python -m full_corpus_pipeline.retrieval \
  --page-text-dir /approved/page_text \
  --manifest step3_pilot/source_metadata/corpus_manifest.parquet \
  --exclude-selection evaluation_sets/unseen_incoming_5_v1/selection.csv \
  --output-dir indexes/corpus_v1
```

Then build/evaluate E0 and E4, run page-cited QA evaluation, test temporary QA on the five unseen PDFs, and permanently ingest them without retraining.
