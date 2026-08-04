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


CROSS_PAGE = """
EASA AD No.: 2025-0058R1
Airworthiness Directive
AD No.: 2025-0058R1
Issued: 19 March 2025
Design Approval Holder’s Name:
AIRBUS S.A.S.
Type/Model designation(s):
A340 aeroplanes
Effective Date: 31 March 2025 (same as original issue)
TCDS Number(s): EASA.A.015
Foreign AD: Not applicable
Revision: This AD revises EASA AD 2025-0058 dated 17 March 2025.
ATA 05 – Time Limits / Maintenance Checks – Airworthiness Limitation Section
Part 4, System Equipment Maintenance Requirements – Amendment
Manufacturer(s):
Airbus, formerly Airbus Industrie
Applicability:
Airbus A340-211 and A340-212 aeroplanes, all manufacturer serial numbers.
Definitions:
The AMP: The Aircraft Maintenance Programme contains the tasks on the basis of which scheduled maintenance is conducted.
For aeroplanes operated under EU regulation the operator or owner ensures
compliance with the AMP as stipulated in Commission Regulation (EU) 1321/2014.
EASA AD No.: 2025-0058R1
TE.CAP.00110-012 © European Union Aviation Safety Agency. All rights reserved. ISO9001 Certified.
Proprietary document. Copies are not controlled. Confirm revision status through the EASA-Internet/Intranet.
An agency of the European Union
Page 2 of 3
New and/or more restrictive tasks: This includes all tasks that are new and all tasks for which a threshold or interval was reduced.
Reason:
Failure to accomplish these instructions could result in an unsafe condition.
Required Action(s) and Compliance Time(s):
Required as indicated by this AD, unless already accomplished:
(1) Within the thresholds and intervals, accomplish all applicable maintenance tasks.
SUPERSEDEDEASA AD No.: 2025-0058R1
TE.CAP.00110-012 © European Union Aviation Safety Agency. All rights reserved. ISO9001 Certified.
Page 3 of 3
(2) If a discrepancy is found, before next flight, accomplish corrective action.
Ref. Publications:
Airbus A340 ALS Part 4, SEMR Variation 8.1 dated 21 December 2023.
Remarks:
1. If requested, EASA can approve Alternative Methods of Compliance for this AD.
5. For any question concerning the technical content of the requirements in this AD, please
contact: AIRBUS – 1IAL (Airworthiness Office), E-mail: airworthiness.A330-A340@airbus.com.
Appendix 1: Data not part of remarks
SHOULD NOT BE IN REMARKS
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

    def test_cross_page_sections_and_printed_metadata_are_preserved(self) -> None:
        row = {
            "text": CROSS_PAGE,
            "ad_number": "2025-0058R1",
            "issue_date": "2025-03-31",  # deliberately wrong manifest value
            "correction_date": "",
            "is_emergency": False,
        }
        record, detail = extract_local_record(row, SCHEMA)

        self.assertEqual("content-local-v2.1.4", detail["parser_version"])
        self.assertEqual("2025-03-19", record["publication"]["issue_date"])
        self.assertEqual("2025-03-31", record["publication"]["effective_date"])
        self.assertEqual("Not applicable", record["publication"]["foreign_ad"])
        self.assertEqual("AIRBUS S.A.S.", record["ad_identity"]["design_approval_holder"])
        self.assertEqual("A340 aeroplanes", record["publication"]["type_model_designation_text"])

        definitions = record["definitions"]["text"]
        self.assertIn("compliance with the AMP", definitions)
        self.assertIn("New and/or more restrictive tasks", definitions)

        action = record["required_actions"][0]["action"]
        self.assertIn("(2) If a discrepancy is found", action)
        for noise in ("Page 2 of 3", "TE.CAP", "SUPERSEDED", "EASA AD No."):
            self.assertNotIn(noise, action)

        remarks = record["remarks"]["text"]
        self.assertIn("airworthiness.A330-A340@airbus.com", remarks)
        self.assertNotIn("SHOULD NOT BE IN REMARKS", remarks)


if __name__ == "__main__":
    unittest.main()
