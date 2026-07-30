# Retrieve and verify the Step 3 sources

`retrieve_pilot_sources.py` retrieves the 30 frozen PDFs listed in
`selection/pilot_selection.csv`, verifies every PDF against its frozen
SHA-256, and extracts one JSON object per PDF page with `pypdf`.

It never writes to `corpus_raw`. Its default outputs are:

```text
step3_pilot/source_pdfs/                 verified PDFs
step3_pilot/page_text/*.pages.jsonl     one JSONL file per PDF
step3_pilot/page_text/pilot_pages.jsonl deterministic combined JSONL
step3_pilot/source_verification_report.json
step3_pilot/source_verification_report.csv
```

## Colab or local setup

Install the page extractor:

```bash
python3 -m pip install "pypdf>=4,<7"
```

Run from the project root:

```bash
python3 step3_pilot/retrieve_pilot_sources.py
```

For an offline integrity/extraction run using PDFs already present in
`source_pdfs`:

```bash
python3 step3_pilot/retrieve_pilot_sources.py --offline
```

Use `--rebuild-page-text` only when intentionally replacing derived JSONL
after changing the extraction-library version. Existing page JSONL is verified
and reused by default.

## Safety and resumability

- The selection must contain exactly 30 unique logical publications.
- Only HTTPS URLs on `easa.europa.eu` or an official subdomain are accepted.
- Redirects outside official EASA HTTPS hosts are rejected.
- Downloads go to `*.pdf.part` and resume with an HTTP Range request when the
  server supports it.
- A partial file becomes the final PDF only after its SHA-256 matches the
  frozen selection and a PDF header is present.
- An existing final PDF with a different hash stops the entire run before any
  new downloads are attempted; it is never overwritten.
- Downloaded mismatches are retained under a timestamped quarantine name and
  never promoted to the final filename.
- Page count must match the frozen manifest value.
- Existing page JSONL must have contiguous pages and valid page-text hashes.
- JSON and CSV verification reports are checkpointed after every document, so
  an interrupted run records its last completed state.

`pypdf` page text will not reproduce the Step 1
`normalized_text_sha256`, which was produced using PyMuPDF normalization. The
utility records that manifest hash for provenance but intentionally verifies
the binary PDF SHA-256 and each newly extracted page-text SHA-256 instead.
