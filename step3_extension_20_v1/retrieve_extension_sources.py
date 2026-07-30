#!/usr/bin/env python3
"""Retrieve and verify the frozen 20-record extension source PDFs.

This reuses the hardened Step 3 downloader without changing the original
30-record pilot defaults.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
sys.path.insert(0, str(PROJECT))

from step3_pilot import retrieve_pilot_sources as core  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    core.EXPECTED_DOCUMENT_COUNT = 20
    forwarded = [
        "--selection",
        str(ROOT / "selection" / "extension_selection.csv"),
        "--pdf-dir",
        str(ROOT / "source_pdfs"),
        "--page-text-dir",
        str(ROOT / "page_text"),
        "--report-json",
        str(ROOT / "source_verification_report.json"),
        "--report-csv",
        str(ROOT / "source_verification_report.csv"),
        "--user-agent",
        "Capstone-Airbus-AD-Extension/1.0 (+research source verification)",
    ]
    if argv:
        forwarded.extend(argv)
    return core.main(forwarded)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
