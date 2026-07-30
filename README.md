# Airbus AD Corpus Manifest

This project converts a folder of EASA Airbus S.A.S. Airworthiness Directive PDFs into a controlled corpus inventory. It detects exact duplicates, text-identical files, corrections, revisions, possible supersedure links, near-duplicate documents, and PDFs that need OCR or manual review.

The source corpus is never changed. All reports are written to a separate output directory.

## Agent handoff

Agents should read these files before continuing the capstone:

- `AGENTS.md`: authoritative scope, safety rules, research contribution, and working protocol.
- `docs/PDF_TO_GOLD_FRAMEWORK.md`: authoritative Step 3 PDF-to-gold lifecycle, batch contract, validation gates, and release rules.
- `docs/PROJECT_STATUS.md`: confirmed progress, missing evidence, blockers, and next actions.
- `docs/CLOUD_WORKFLOW.md`: GitHub/Google Drive boundaries and the Colab handoff procedure.
- `docs/PROJECT_PLAN.md`: exact 13 July-30 September execution plan and completion gates.
- `docs/BENCHMARK_DESIGN.md`: fixed 100-AD/150-question/30-summary core and optional extension rules.
- `docs/DECISIONS.md`: stable methodological decisions and change record.
- `dataset_framework/BATCH_CHECKLIST.md`: operational checklist for each versioned Step 3 batch.

## Why this exists

The manifest is the control layer between the raw PDFs and later extraction, classification, summarization, and RAG work. It prevents duplicated or outdated AD versions from silently entering experiments and gives every physical file a stable identifier.

EASA AD conventions handled by the parser include:

- Original: `2023-0123`
- Revision: `2023-0123R1`
- Emergency AD: `2023-0123-E`
- Correction: same AD number with a notice such as `[Corrected: 12 August 2023]`

## Project structure

```text
Capstone/
├── 01_build_ad_corpus_manifest.ipynb
├── step2_ad_schema/
│   ├── easa_airbus_ad_annotation.schema.json
│   ├── annotation_guidelines.md
│   └── validate_annotations.py
├── step3_pilot/
├── step3_extension_20_v1/
├── dataset_framework/
│   ├── BATCH_CHECKLIST.md
│   ├── script_registry.json
│   └── validate_gold_release.py
├── docs/
│   ├── PDF_TO_GOLD_FRAMEWORK.md
│   ├── BENCHMARK_DESIGN.md
│   ├── DECISIONS.md
│   ├── PROJECT_PLAN.md
│   └── PROJECT_STATUS.md
├── AGENTS.md
└── README.md
```

## Step 3 PDF-to-gold workflow

All Step 3 work follows `docs/PDF_TO_GOLD_FRAMEWORK.md`. The allowed lifecycle is:

```text
selected
  -> source_verified
  -> machine_first_pass
  -> human_review_pending
  -> human_review_in_progress
  -> human_approved
  -> gold_validated
  -> gold_published
```

Key boundaries:

- frozen selections, canonical sources, and `human_review_queue/` are read-only;
- only `human_review_working/` is editable during review;
- automated extraction and validation cannot grant human approval;
- approved working files must pass the strict schema, evidence, and reusable release validators;
- gold is published as a new versioned release with hashes, manifests, release notes, and Drive readback; and
- the 30-record pilot and combined 50-record release are intermediate releases toward the fixed 100-AD research core, not the optional 200-record stretch.

Use `step3_pilot/validate_step3_pilot.py` only for the frozen 30-record pilot. Use `dataset_framework/validate_gold_release.py` for the 20-record batch, combined 50-record release, and later release sizes.

## Google Drive layout

GitHub stores the versioned implementation and audit trail. Google Drive stores
the immutable PDF corpus and large reproducible derivatives. See
`docs/CLOUD_WORKFLOW.md` before starting a fresh Colab runtime.

Create this layout in Google Drive:

```text
My Drive/
└── Capstone_AD_Project/
    ├── corpus_raw/
    │   ├── first_ad.pdf
    │   └── ...
    └── metadata/
```

The input folder may contain subfolders. PDF discovery is recursive.

## Run in Google Colab

1. Put this project folder in `My Drive/Capstone_AD_Project/`.
2. Open `01_build_ad_corpus_manifest.ipynb` in Colab.
3. Run all cells.
4. Review the generated reports under `metadata/`.

The current manifest implementation is self-contained in the notebook; this
repository does not yet expose it as an installable command-line package. The
notebook installs its runtime dependencies, mounts Drive, reads
`Capstone_AD_Project/corpus_raw`, and writes reports to
`Capstone_AD_Project/metadata`.

The default near-duplicate threshold in the notebook is `0.92`. Change
`NEAR_DUPLICATE_THRESHOLD` in the configuration cell only when intentionally
running and recording a different review threshold.

## Generated artifacts

| File | Purpose |
| --- | --- |
| `corpus_manifest.csv` | Human-readable master inventory |
| `corpus_manifest.xlsx` | Review-friendly Excel copy |
| `corpus_manifest.parquet` | Typed, compressed manifest for code |
| `corpus_extracted_text.parquet` | Extracted text cache for later NLP/RAG work |
| `duplicate_review.csv` | Exact duplicate groups and same-version conflicts |
| `version_chains.csv` | Original, revision, correction, previous, next, and latest relationships |
| `near_duplicate_candidates.csv` | High-similarity pairs requiring review |
| `supersedure_links.csv` | Candidate cross-AD supersedure relationships with evidence |
| `processing_and_metadata_review.csv` | OCR failures, missing IDs, and metadata problems |
| `manual_overrides.csv` | Stable location for corpus-manifest corrections; never edit the generated manifest directly |
| `corpus_summary.json` | Corpus-level counts and quality indicators |

## Duplicate categories

- `exact_binary_duplicate`: the SHA-256 hashes of the PDF files are identical.
- `exact_text_duplicate`: PDF bytes differ, but normalized extracted text is identical.
- `same_ad_version_different_content`: the same logical AD version appears more than once with different content. This always requires manual review.
- Near-duplicate pairs are suggestions only. Revisions and corrections are expected to be near duplicates and must not be deleted.

## Safe review policy

Do not delete, rename, or overwrite files in `corpus_raw` during manifest construction. Even a file marked `safe_duplicate_candidate` must be opened and reviewed before any later quarantine decision. Record corpus-manifest decisions in `manual_overrides.csv`; Step 3 annotation corrections belong only in the batch `human_review_working/` folder.

## Development

Run the current schema and Step 3 tests:

```bash
python3 -m unittest discover -s step2_ad_schema/tests -v
python3 -m unittest discover -s step3_pilot/tests -v
```
