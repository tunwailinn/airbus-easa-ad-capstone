# Corpus identity audit

Date: 11 September 2026

## Result

The frozen local snapshot contains **1,809 PDF files**, **1,809 unique file hashes**, and **1,808 distinct base AD numbers**. All 1,809 file hashes match the saved manifest. Independently checked PDF header identifiers agree with all 1,809 manifest AD identifiers after resolving three header-format exceptions.

- 1,807 base AD numbers have one stored PDF each.
- One base AD number, 2009-0113, has two stored PDFs: 2009-0113 dated 27 May 2009 and 2009-0113R1 dated 4 March 2010.
- There are 345 revised-version PDFs. Of these, 344 have no other version of the same base AD number in this snapshot.
- Thus 1,807 + 2 = 1,809 files, and 1,807 + 1 = 1,808 base numbers.

## Meaning and limitation

A base AD number removes the revision suffix from an AD identifier: for example, 2009-0113R1 becomes 2009-0113. It does not mean an aircraft model family, and it does not group different AD numbers linked by supersedure. The corpus is not a complete archive of every original and revision for its 1,808 base numbers.

The downloader collects PDF attachments exposed in filtered EASA search-result rows; it does not recursively reconstruct each directive's complete historical revision chain. Both 2009-0113 files were downloaded under the search record labeled 2009-0113R1. One downloaded filename therefore starts with R1 even though the authoritative PDF header identifies the original 2009-0113 publication. The manifest correctly records that header/filename mismatch.

## Independent verification

Every local PDF was opened directly with PyMuPDF, and its first-page AD identifier was compared with the source manifest. Three exceptions needed additional handling:

- 2006-0309R1: AD Nr. rather than AD No.
- 2007-0080R1: printed as 2007- 0080-R1.
- 2012-0088: malformed text extraction; the original rendered first page was visually checked and clearly reads 2012-0088.

The download log has four additional unique filenames absent from this snapshot: an EASA comment-response document, two FAA AD PDFs, and an EASA position document on an FAA AD. These are not four missing EASA AD PDFs. All 1,809 local PDF filenames are represented in the log.

## Recommended paper wording

The frozen snapshot contains 1,809 PDF documents covering 1,808 distinct base AD numbers. Most base numbers are represented by a single stored version; both the original and revision R1 are retained for AD 2009-0113. The snapshot does not contain complete revision histories.

## Sources

- corpus_raw/*.pdf
- step3_pilot/source_metadata/corpus_manifest.parquet
- easa_airbus_ad_manifest.csv
- build_colab_notebook.py: parse_ad_components and find_ad_number
- download_airbus_ads_to_drive.py: extract_page_pdfs

The accompanying verified_identifiers.csv records the file-level comparison. No source PDFs, frozen manifests, parsers, or evaluation artifacts were changed.
