# Cloud workflow

This project uses GitHub for versioned code and audit artifacts and Google
Drive for the canonical PDF corpus and large reproducible derivatives.

## Versioned in GitHub

- Colab notebooks and Python utilities
- Step 2 schemas, guidelines, vocabularies, examples, and tests
- Step 3 frozen selections and source hashes
- source-verification reports and visual-review records
- annotation packets, immutable review queues, editable working records,
  submissions, adjudication artifacts, and validation reports
- dataset release gates, project decisions, plans, and status documentation
- versioned review outputs under `outputs/`

## Retained in Google Drive

- `corpus_raw/`
- batch `source_pdfs/`
- batch `page_text/`
- temporary PDF renders and contact sheets
- OAuth credentials and tokens
- generated handoff ZIP archives

The Drive project root is:

```text
My Drive/
└── Capstone_AD_Project/
    ├── corpus_raw/
    └── metadata/
        ├── step2_ad_schema_and_guidelines/
        ├── step3_pilot_v1/
        └── step3_extension_20_v1/
```

Do not copy credentials, tokens, or private keys into GitHub, notebooks, or
Drive-shared folders.

## Start in Google Colab

1. Open `01_build_ad_corpus_manifest.ipynb` from this repository or the
   verified Drive copy.
2. Mount Google Drive when prompted.
3. Confirm the project root is
   `/content/drive/MyDrive/Capstone_AD_Project`.
4. Keep `corpus_raw/` read-only and write generated corpus reports only under
   `metadata/`.
5. For Step 3, use the versioned batch directory in Drive for canonical PDFs
   and page text. Use the matching scripts, selections, annotations, and
   validators from this repository.
6. Read generated files back from Drive and verify exact counts, filenames,
   hashes, and validation reports before claiming completion.

For a private repository clone, authenticate with a GitHub token stored in
Colab Secrets or use a notebook already copied to Drive. Never place a token
directly in a notebook cell.

## Step 3 validation boundary

Automated validation does not grant human approval. Follow
`docs/PDF_TO_GOLD_FRAMEWORK.md` and keep the lifecycle linear:

```text
selected
  → source_verified
  → machine_first_pass
  → human_review_pending
  → human_review_in_progress
  → human_approved
  → gold_validated
  → gold_published
```

Run `step3_pilot/validate_step3_pilot.py` only for the frozen 30-record pilot.
Use `dataset_framework/validate_gold_release.py` for extension, combined, and
later versioned releases.
