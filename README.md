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
- Local parser: **`content-local-v2.1.5`**
- Extraction evaluator: **`content-eval-v3.1.5`**
- Immutable audit source: `gold_releases/easa_airbus_ad_gold_v2/`
- Active content benchmark: `easa_airbus_ad_content_gold_50_v2`
- Nominal split: 30 development / 20 test, seed 42
- QA benchmark: `easa_airbus_ad_qa_50_v2`
- Unseen ingestion set: 5 PDFs

The previously generated v2.1.4 run is now **stale** and must not be promoted:

```text
data_processed/runs/local-content-development-1804-v2.1.4/
```

The next run/canonical targets are:

```text
data_processed/runs/local-content-development-1804-v2.1.5/
data_processed/canonical_content_v2.1.5/
```

## Why v2.1.5 exists

Development evaluation of v2.1.4 showed strong stable metadata performance but exposed remaining deterministic-format defects. v2.1.5 adds development-only fixes for:

- legacy `EASA Form 110 Page x/y` and `Page x/y` furniture, including embedded page headers;
- multi-line headings such as `Required Action(s) / and Compliance / Time(s):`;
- DAH field fall-through into `Type/Model designation(s)` text;
- legacy Airbus records with no explicit DAH-name field, using a conservative Airbus-manufacturer fallback only for non-STC/non-modification documents;
- complete legacy subject wording around ATA headings, including multi-ATA forms such as `ATA 26/29`;
- legacy France TCDS identifiers;
- false aircraft-model matches inside publication IDs such as `A350-52-P012`;
- broader deterministic publication-reference identifiers from the printed reference section; and
- direct original-issue supersedure wording inside revision statements.

The evaluator was updated at the same time so malformed holder extraction is reported as **unknown**, not silently counted as out-of-scope, raw-section presence is driven by actual source headings when the source-text cache is available, and uppercase PDF status watermarks are distinguished from ordinary prose such as `which is superseded`.

## Run tests

```bash
.venv/bin/python -m unittest discover -s full_corpus_pipeline/tests -v
```

The regression suite contains only development-derived format cases plus the previously disclosed parser spot-check regressions. Do not add new locked-test content while tuning v2.1.5.

## Regenerate the nominal 1,804 development records

```bash
.venv/bin/python -m full_corpus_pipeline.extract_corpus \
  --run-id local-content-development-1804-v2.1.5
```

Do not overwrite or relabel the v2.1.4 run.

## Audit the 30 nominal development references

```bash
.venv/bin/python -m full_corpus_pipeline.audit_development_reference \
  --output data_processed/runs/local-content-development-1804-v2.1.5/development_reference_audit.json
```

The current immutable development audit has 30 nominal members and two known holder-scope exclusions discovered before v2.1.5:

- `2024-0095` — Airbus Defence and Space S.A.
- `2026-0079` — Lufthansa Technik AG

They remain in the immutable 50-record audit release but are not primary Airbus S.A.S. development scores.

## Audit all 1,804 generated records for holder scope

```bash
.venv/bin/python -m full_corpus_pipeline.audit_corpus_scope \
  data_processed/runs/local-content-development-1804-v2.1.5/records \
  --output data_processed/runs/local-content-development-1804-v2.1.5/corpus_scope_audit.json
```

The v2.1.4 scope report (`1729 eligible / 59 excluded / 16 unknown`) must **not** be used as the final corpus count. Many of its `excluded` strings were actually DAH parser boundary failures such as Type/Model text. Evaluator v3.1.5 treats malformed holder values as `unknown`, and parser v2.1.5 fixes the underlying legacy-header extraction. Use only the regenerated v2.1.5 scope report for the next corpus-governance decision.

## Run development extraction evaluation

```bash
.venv/bin/python -m full_corpus_pipeline.evaluate_extraction \
  data_processed/runs/local-content-development-1804-v2.1.5/records \
  --output data_processed/runs/local-content-development-1804-v2.1.5/evaluation_development_v3.1.5.json \
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

Before touching the test split, verify all of the following on v2.1.5:

1. 1,804 requested records, 1,804 successful records, zero extraction failures.
2. 100% prediction coverage and schema validity on the scored development set.
3. No unexpected missing printed Required Actions/Compliance sections.
4. No material repeated EASA page furniture in preserved raw sections.
5. DAH/scope audit no longer classifies malformed Type/Model prose as genuine out-of-scope holders.
6. Remaining reference-ID misses are documented and acceptable or fixed from development evidence only.
7. Representative source-PDF spot checks pass.

If a genuine defect remains, fix it from eligible development evidence only and version the parser again. Do not inspect locked-test compliance labels to tune extraction.

## Final clean extraction evaluation

Only after development behavior is frozen:

```bash
.venv/bin/python -m full_corpus_pipeline.evaluate_extraction \
  data_processed/runs/local-content-development-1804-v2.1.5/records \
  --output data_processed/runs/local-content-development-1804-v2.1.5/evaluation_test_clean_v3.1.5.json \
  --split test
```

The nominal 20-record test split remains immutable. `2024-0038` is automatically excluded from clean test scoring because it was previously used to diagnose parser defects. Holder-scope exclusions are derived separately from reviewed gold metadata. Use the generated report's `record_count` as the actual clean test sample size.

## Promote only after validation

```bash
.venv/bin/python -m full_corpus_pipeline.promote_extraction_run \
  data_processed/runs/local-content-development-1804-v2.1.5 \
  data_processed/canonical_content_v2.1.5 \
  --expected-count 1804
```

Promotion still preserves one generated content record per nominal physical development PDF. If the final research application needs a strict Airbus S.A.S.-only operational subset, implement that as an explicit scope sidecar/filter after the v2.1.5 scope audit; do not silently delete records or rewrite the immutable source inventory.

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
