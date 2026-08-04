from __future__ import annotations

import unittest

from full_corpus_pipeline.local_extractor_v216 import (
    _header_manufacturer,
    _header_subject_and_ata,
    _repair_applicability,
)


class ParserV216CatalogueTests(unittest.TestCase):
    def test_legacy_subject_wraps_around_ata_line(self) -> None:
        text = """
Foreign AD: Not applicable
Supersedure: None
Fire Protection / Hydraulic Power - Air Pressurisation Check Valves
ATA 26, 29
– Identification / Replacement
Manufacturer(s): AIRBUS (formerly AIRBUS INDUSTRIE).
Applicability: A300 aeroplanes.
"""
        subject, chapters = _header_subject_and_ata(text)
        self.assertEqual(
            "Fire Protection / Hydraulic Power - Air Pressurisation Check Valves – Identification / Replacement",
            subject,
        )
        self.assertEqual(["26", "29"], [item["code"] for item in chapters])

    def test_lifecycle_continuation_is_not_subject_prefix(self) -> None:
        text = """
Foreign AD: Not applicable
Supersedure: This AD supersedes EASA AD 2018-0255 dated 27 November 2018 and EASA AD
2019-0106 dated 15 May 2019.
ATA 25 – Equipment / Furnishings – Galley / Container End Stop – Replacement
Manufacturer(s): Airbus
Applicability: A320 aeroplanes.
"""
        subject, chapters = _header_subject_and_ata(text)
        self.assertEqual(
            "Equipment / Furnishings – Galley / Container End Stop – Replacement",
            subject,
        )
        self.assertEqual(["25"], [item["code"] for item in chapters])

    def test_manufacturer_cell_does_not_absorb_applicability(self) -> None:
        text = """
ATA 26, 29 – Fire Protection / Hydraulic Power
Manufacturer(s):      AIRBUS (formerly AIRBUS INDUSTRIE).
AIRBUS A300, A310 and A300-600 aeroplanes, all certified models, all serial
Applicability:          numbers, and AIRBUS A300F4-608ST aeroplanes, all serial numbers.
Reason: Example.
"""
        self.assertEqual(
            "AIRBUS (formerly AIRBUS INDUSTRIE).",
            _header_manufacturer(text),
        )

    def test_applicability_repairs_two_column_prefix_and_spaced_models(self) -> None:
        text = """
Manufacturer(s): Airbus
AIRBUS A320- 111, A320-211 and A321- 212 aeroplanes, all serial
Applicability: numbers, and A300F4-608ST aeroplanes.
Reason: Example.
"""
        record = {
            "applicability": [
                {
                    "text": "numbers, and A300F4-608ST aeroplanes.",
                    "aircraft_families": ["A300"],
                    "models": ["A300F4-608ST"],
                }
            ]
        }
        _repair_applicability(text, record)
        item = record["applicability"][0]
        self.assertTrue(item["text"].startswith("AIRBUS A320- 111"))
        self.assertIn("A320-111", item["models"])
        self.assertIn("A321-212", item["models"])
        self.assertIn("A300F4-608ST", item["models"])
        self.assertNotIn("A320", item["models"])

    def test_only_false_a300_reference_model_is_omitted(self) -> None:
        text = """
Manufacturer(s): Airbus
Applicability: Refer to Airbus A300-24 instructions.
Reason: Example.
"""
        record = {
            "applicability": [
                {
                    "text": "Refer to Airbus A300-24 instructions.",
                    "aircraft_families": ["A300"],
                    "models": ["A300-24"],
                }
            ]
        }
        _repair_applicability(text, record)
        item = record["applicability"][0]
        self.assertNotIn("models", item)
        self.assertNotIn("aircraft_families", item)


if __name__ == "__main__":
    unittest.main()
