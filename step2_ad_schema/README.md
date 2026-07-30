# Step 2 — EASA Airbus AD annotation contract

Version **1.0.0** defines the JSON record used to annotate one canonical EASA
Airworthiness Directive publication, including its source provenance, evidence
spans, requirements, compliance logic, and document relationships.

## Package contents

- `easa_airbus_ad_annotation.schema.json` — normative JSON Schema, Draft 2020-12.
- `annotation_guidelines.md` — normative human annotation rules and QC workflow.
- `controlled_vocabularies.json` — plain-language descriptions of enum values.
- `blank_ad_annotation.json` — structurally valid draft to copy for a new record.
- `examples/2007-0178.annotation.json` — fully evidenced, approved example.
- `validate_annotations.py` — structural and cross-field semantic validator.
- `tests/test_validation.py` — positive and deliberately invalid regression cases.
- `COLAB_USAGE.md` — copy/paste cells for the Drive-resident workflow.

The Schema controls shape, types, required keys, formats, and vocabularies. The
Python validator additionally resolves evidence and object references, checks AD
identity consistency, protects historical mentions from being promoted to
supersedure, enforces independent review, and applies approval gates.

## Annotation unit

Create one record for each canonical logical publication:

- each original, revision, emergency issue, or correction gets its own record;
- byte-identical aliases reuse the canonical record from Step 1;
- near duplicates remain separate unless a human confirms they are aliases;
- all records in a revision/correction family share `base_ad_number` and
  `benchmark_metadata.split_group`, preventing train/test leakage.

The source PDF remains read-only. Copy manifest identifiers and hashes into
`source_document`; never fabricate them.

## Validate

From the project directory:

```bash
python3 step2_ad_schema/validate_annotations.py \
  step2_ad_schema/blank_ad_annotation.json

python3 step2_ad_schema/validate_annotations.py --strict \
  step2_ad_schema/examples/2007-0178.annotation.json

python3 -m unittest discover -s step2_ad_schema/tests -v
```

Pass multiple annotation files to one validator command (or use a shell-expanded
list) to activate corpus-level leakage checks across AD families and duplicate or
near-duplicate clusters and to resolve correction target records. Files from one
group may not span train, validation, and test. When intentionally validating a
single record whose target is outside the supplied batch, use
`--allow-unresolved-targets`; the validator prints a warning because referential
integrity was not checked.

Normal validation accepts an incomplete record whose status is `draft`, but it
still checks all populated references. `--strict` requires an approved,
human-confirmed record with evidence, requirements, applicability, and review
history. Use strict validation before setting `gold_record` or admitting a record
to evaluation data.

Dependency: Python 3.10+ and `jsonschema` with Draft 2020-12 support.

For Google Colab, follow `COLAB_USAGE.md`; it mounts Drive, installs the single
validator dependency, and validates directly inside the metadata folder.

## Versioning

Pin both `schema_version` and `annotation_metadata.guideline_version`. A breaking
field or meaning change increments the major version; backward-compatible field
additions increment the minor version; documentation or validator corrections
increment the patch version. Do not silently rewrite already approved records.
