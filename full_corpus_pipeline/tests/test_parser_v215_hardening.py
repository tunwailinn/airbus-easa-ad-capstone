from __future__ import annotations

import unittest

from full_corpus_pipeline.local_extractor import _reference_candidates, _subject_and_ata


class ParserV215HardeningTests(unittest.TestCase):
    def test_subject_keeps_post_ata_continuation_line(self) -> None:
        text = """
ATA 05 – Time Limits / Maintenance Checks – Airworthiness Limitation Section
Part 4, System Equipment Maintenance Requirements – Amendment
Manufacturer(s): Airbus
Applicability: A340 aeroplanes.
"""
        subject, chapters = _subject_and_ata(text)
        self.assertIn("Airworthiness Limitation Section", subject or "")
        self.assertIn("Part 4, System Equipment Maintenance Requirements", subject or "")
        self.assertEqual(["05"], [item["code"] for item in chapters])

    def test_reference_candidates_exclude_easa_ad_lifecycle_numbers(self) -> None:
        section = """
Airbus Service Bulletin A320-27-1243.
EASA AD 2015-0087 is mentioned for lifecycle history.
Vendor document F-1996-177-038(B)R1.
"""
        values = {number for number, _ in _reference_candidates(section)}
        self.assertIn("A320-27-1243", values)
        self.assertIn("F-1996-177-038(B)R1", values)
        self.assertNotIn("2015-0087", values)


if __name__ == "__main__":
    unittest.main()
