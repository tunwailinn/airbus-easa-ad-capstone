# Layer A — Section-Complete Content Catalogue

Layer A creates and validates deterministic section-complete Airbus EASA AD content records.

## Why the implementation files remain at the package root

The active Layer A parser/evaluation artifacts are frozen thesis artifacts. Their recorded paths and behavior are preserved rather than rewritten only for cosmetic folder cleanup. This folder is the canonical navigation index for Layer A.

## Canonical Layer A modules

### Extraction and schema

- `../content_record.schema.json` — content schema v2.1.0
- `../local_extractor_v216.py` — frozen parser `content-local-v2.1.6`
- `../local_extractor.py` — retained extractor compatibility/history
- `../extract_corpus.py` — full-corpus extraction runner
- `../content_projection.py` — active evaluation projection
- `../build_projection_lineage.py` — projection lineage helper
- `../validate_content_dataset.py` — content dataset validation
- `../promote_extraction_run.py` — canonical-run promotion

### Evaluation and scope

- `../evaluate_extraction.py` — extraction evaluator
- `../audit_corpus_scope.py` — strict Airbus scope audit
- `../scope_policy.py` — holder-scope rules
- `../scope_review_overrides.json` — reviewed scope overrides
- `../lifecycle.py` — lifecycle/snapshot helper logic
- `../audit_development_reference.py` — development reference audit
- `../freeze_evaluation_design.py` — evaluation split/design freeze support

## Frozen boundary

Do not retune or modify Layer A from locked extraction-test outcomes. In particular, parser v2.1.6 remains frozen. Layer C results must never trigger Layer A parser changes.

## Output boundary

Layer A is responsible for structured metadata, section-complete raw difficult sections, scope/lifecycle support, and deterministic catalogue behavior. Detailed compliance interpretation remains a Layer B + Layer C responsibility.
