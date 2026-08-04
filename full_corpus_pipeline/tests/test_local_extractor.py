from __future__ import annotations

import json
import unittest
from pathlib import Path

from full_corpus_pipeline.local_extractor import extract_local_record


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads(
    (ROOT / "full_corpus_pipeline/content_record.schema.json").read_text(encoding="utf-8")
)


SAMPLE = """
EASA AD No.: 2026-0123R1
Airworthiness Directive
AD No.: 2026-0123R1
Issued: 12 July 2026

Design Approval Holder’s Name:          Type/Model designation(s):
Airbus S.A.S.                            A320-214 and A320-216 aeroplanes

Effective Date: Revision 1: 20 July 2026
TCDS Number(s): EASA.A.064
Foreign AD: Not applicable
Supersedure: This AD supersedes EASA AD 2025-0001 dated 10 January 2025.

ATA 27 – Flight Controls – Inspection
Manufacturer(s): Airbus
Applicability: A320-214 and A320-216 aeroplanes, all manufacturer serial numbers.
Definitions: The affected part is the actuator identified in Airbus SB A320-27A1234.
Reason: Cracks were detected.
Required Action(s) and Compliance Time(s):
(1) Within 500 flight cycles, inspect the affected area in accordance with Airbus SB A320-27A1234.
(2) If a crack is found, contact Airbus before next flight.
Ref. Publications:
Airbus Alert Service Bulletin A320-27A1234 original issue dated 01 June 2026.
Remarks:
For further information contact EASA.
"""


class LocalExtractorTests(unittest.TestCase):
    def test_extracts_all_sections_without_interpreting_compliance(self) -> None:
        row = {
            "text": SAMPLE,
            "ad_number": "2026-0123R1",
            "issue_date": "2026-07-12",
            "correction_date": "",
            "is_emergency": False,
        }
        record, detail = extract_local_record(row, SCHEMA)
        self.assertEqual("deterministic_local", detail["method"])
        self.assertEqual("R1", record["ad_identity"]["revision"])
        self.assertEqual("Airbus S.A.S.", record["ad_identity"]["design_approval_holder"])
        self.assertEqual("2026-07-20", record["publication"]["effective_date"])
        self.assertEqual(["A320-214", "A320-216"], record["publication"]["type_model_designations"])
        self.assertIn("Within 500 flight cycles", record["required_actions"][0]["action"])
        self.assertNotIn("initial_compliance", record["required_actions"][0])
        self.assertIn("affected part", record["definitions"]["text"])
        self.assertEqual("Cracks were detected.", record["reason"]["text"])
        self.assertIn("Airbus Alert Service Bulletin", record["referenced_publications_text"]["text"])
        self.assertIn("further information", record["remarks"]["text"])
        self.assertEqual("A320-27A1234", record["referenced_publications"][0]["number"])
        self.assertEqual(["2025-0001"], record["supersedure"]["superseded_ad_numbers"])

    def test_rejects_manifest_identity_disagreement(self) -> None:
        row = {
            "text": SAMPLE,
            "ad_number": "2026-9999",
            "issue_date": "2026-07-12",
            "correction_date": "",
            "is_emergency": False,
        }
        with self.assertRaisesRegex(ValueError, "disagrees with manifest"):
            extract_local_record(row, SCHEMA)


if __name__ == "__main__":
    unittest.main()
