# Dataset expansion framework

Start with
[`docs/PDF_TO_GOLD_FRAMEWORK.md`](../docs/PDF_TO_GOLD_FRAMEWORK.md).

This directory contains:

- `BATCH_CHECKLIST.md`: the checklist copied into each new annotation batch;
- `script_registry.json`: machine-readable ownership and reusability notes for
  the scripts used in the pilot and 20-record extension;
- `validate_gold_release.py`: the batch-size-independent final gold gate.

The framework does not promote machine-generated annotations. Human review,
explicit approval, strict validation, and versioned publication remain
separate required gates.
