from __future__ import annotations

import sys
import unittest
from pathlib import Path


PILOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PILOT_DIR))

from build_section_index import (  # noqa: E402
    InputError,
    SECTION_ORDER,
    _reject_excluded_input,
    build_index,
    detect_page_headings,
    load_and_verify_pages,
    load_selection,
    sha256_path,
)


class SectionIndexTests(unittest.TestCase):
    def test_current_frozen_inputs_build_exact_30_record_index(self) -> None:
        selection_path = PILOT_DIR / "selection" / "pilot_selection.json"
        page_text_path = PILOT_DIR / "page_text" / "pilot_pages.jsonl"
        selection = load_selection(selection_path)
        pages = load_and_verify_pages(page_text_path, selection)
        index = build_index(
            selection,
            pages,
            selection_sha256=sha256_path(selection_path),
            page_text_sha256=sha256_path(page_text_path),
            page_text_source="page_text/pilot_pages.jsonl",
        )
        self.assertEqual(index["record_count"], 30)
        self.assertEqual(index["page_record_count"], 171)
        self.assertEqual(len(index["records"]), 30)
        for record in index["records"]:
            for section in SECTION_ORDER:
                for page_number in record["sections"][section]["pages"]:
                    self.assertGreaterEqual(page_number, 1)
                    self.assertLessEqual(page_number, record["page_count"])

    def test_modern_and_legacy_required_action_headings(self) -> None:
        text = "\n".join(
            [
                "Required Action(s) and Compliance Time(s):",
                "Required Action(s) Required as indicated, unless accomplished previously:",
                "Required Action(s) 1. Required as indicated:",
                "Compliance: Required as indicated:",
            ]
        )
        matches = detect_page_headings(text)
        self.assertEqual(
            [item["section"] for item in matches],
            ["required_actions_compliance"] * 4,
        )

    def test_body_table_reference_is_not_promoted_to_heading(self) -> None:
        matches = detect_page_headings(
            "Within the limit specified in Table 1 of this AD.\n"
            "Table 1 of this AD provides the threshold.\n"
            "Table 1 – Inspection Threshold"
        )
        table_matches = [
            item for item in matches if item["section"] == "appendix_table"
        ]
        self.assertEqual(len(table_matches), 1)
        self.assertEqual(table_matches[0]["text"], "Table 1 – Inspection Threshold")

    def test_excluded_page_text_location_is_rejected(self) -> None:
        with self.assertRaises(InputError):
            _reject_excluded_input(
                PILOT_DIR
                / "excluded_after_selection_audit"
                / "page_text"
                / "old.pages.jsonl"
            )


if __name__ == "__main__":
    unittest.main()
