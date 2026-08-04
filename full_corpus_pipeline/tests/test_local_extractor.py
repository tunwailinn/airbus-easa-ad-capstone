from __future__ import annotations

import json
import unittest
from pathlib import Path

from full_corpus_pipeline.local_extractor import extract_local_record, _clean_layout_text

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "full_corpus_pipeline/content_record.schema.json").read_text(encoding="utf-8"))

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
Ref. Publications:
Airbus Alert Service Bulletin A320-27A1234 original issue dated 01 June 2026.
Remarks:
For further information contact EASA.
"""

LEGACY_2009_0141 = """
EASA AD No.: 2009-0141
EASA Form 110 Page 1/8
EASA AIRWORTHINESS DIRECTIVE
AD No.: 2009-0141
Date: 02 July 2009
TCDS Number : EASA.A.064
Foreign AD : Not applicable
Supersedure : None
Stabilizers – Rudder Side Shell Skin – Inspection
ATA 55
Manufacturer(s): Airbus (formerly Airbus Industrie)
Applicability: Airbus A318-111 and A320-111 aeroplanes.
Definitions:
Affected rudders are those identified in Airbus AOT A320-55A1038.
Reason:
Cracks were detected.
SUPERSEDEDEASA AD No.: 2009-0141
EASA Form 110 Page 2/8
Effective Date: 16 July 2009
Required action(s)
and Compliance
Time(s):
Required as indicated, unless already accomplished.
(1) Inspect the affected rudder.
SUPERSEDEDEASA AD No.: 2009-0141
EASA Form 110 Page 3/8
(2) Report the inspection results.
Ref. Publications:
Airbus Alert Operator Transmission A320-55A1038.
Technical Disposition TD/K4/S2/27051/2009.
Remarks:
1. EASA can approve Alternative Methods of Compliance.
"""

LEGACY_2009_0171 = """
EASA AD No : 2009-0171
EASA Form 110 Page 1/3
EASA AIRWORTHINESS DIRECTIVE
AD No.: 2009-0171
Date: 05 August 2009
TCDS Number : EASA.A.014, France N° 145
Foreign AD : Not applicable
Fire Protection / Hydraulic Power - Air Pressurisation Check Valves – Identification / Replacement
ATA 26/29
Manufacturer(s): Airbus (formerly Airbus Industrie)
Applicability: Airbus A300, A310 and A300F4-608ST aeroplanes.
Reason: An unsafe condition was identified.
EASA AD No : 2009-0171
EASA Form 110 Page 2/3
Effective Date: 19 August 2009
Required Action(s)
and Compliance
Time(s):
Required as indicated.
(1) Inspect the check valves.
EASA AD No : 2009-0171
EASA Form 110 Page 3/3
(2) Replace affected valves.
Ref. Publications:
Airbus SB A300-29-6060, A300-29-9009, A310-29-2097 and A300-29-0124.
Vendor document 20070407-29-1 and 29-020.
Remarks: None.
"""

MODERN_COLLAPSED = """
EASA AD No.: 2008-0012
Airworthiness Directive
AD No.: 2008-0012
Date: 14 January 2008
Design Approval Holder's Name: Type/Model designation(s):
Airbus A330 and A340-200/-300 series aircraft
Effective Date: 28 January 2008
TCDS Number(s): EASA.A.004, EASA.A.015
Foreign AD: Not applicable
Stabilizers - Carbon Fiber Reinforced Plastic (CFRP) Rudder - Inspection / Repair ATA 55
Manufacturer(s): Airbus
Applicability: Airbus A330-301, A340-200 and A340-300 aeroplanes.
Reason: Rudder damage was found.
Required Action(s): Inspect the rudder.
Ref. Publications: Airbus SB A330-55-3016 and A340-55-4017.
Remarks: None.
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
Manufacturer(s): Airbus, formerly Airbus Industrie
Applicability: Airbus A340-211 and A340-212 aeroplanes, all manufacturer serial numbers.
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

REFERENCE_RICH = """
EASA AD No.: 2015-0135R3
Airworthiness Directive
AD No.: 2015-0135R3
Issued: 01 July 2015
Design Approval Holder’s Name: Airbus S.A.S.
Type/Model designation(s): A318, A319, A320 and A321 aeroplanes
Effective Date: 15 July 2015
TCDS Number(s): EASA.A.064
Foreign AD: Not applicable
Revision: This AD revises EASA AD 2015-0135R2. The original issue of this AD superseded EASA AD 2015-0087.
ATA 34 – Navigation – Flight Management – Modification
Manufacturer(s): Airbus
Applicability: Airbus A320-214 aeroplanes.
Reason: Unsafe condition.
Required Action(s) and Compliance Time(s): Accomplish the modification.
Ref. Publications:
Airbus Service Bulletins A320-27-1243, A320-27-1244, A320-34-1415 and A320-34-1610.
Airbus OIT999.0015/15.
Vendor C16291A-34-007 and C16291A-34-009.
AFMA320TR502.
Remarks: None.
"""

class LocalExtractorTests(unittest.TestCase):
    def row(self, text: str, ad: str, issue: str = "") -> dict:
        return {"text": text, "ad_number": ad, "issue_date": issue, "correction_date": "", "is_emergency": False}

    def test_rejects_manifest_identity_disagreement(self) -> None:
        with self.assertRaisesRegex(ValueError, "disagrees with manifest"):
            extract_local_record(self.row(SAMPLE, "2026-9999"), SCHEMA)

    def test_cross_page_v214_regression_remains_fixed(self) -> None:
        record, _ = extract_local_record(self.row(CROSS_PAGE, "2025-0058R1", "2025-03-31"), SCHEMA)
        self.assertEqual("2025-03-19", record["publication"]["issue_date"])
        self.assertEqual("AIRBUS S.A.S.", record["ad_identity"]["design_approval_holder"])
        self.assertIn("New and/or more restrictive tasks", record["definitions"]["text"])
        action = record["required_actions"][0]["action"]
        self.assertIn("(2) If a discrepancy is found", action)
        for noise in ("Page 2 of 3", "TE.CAP", "SUPERSEDED", "EASA AD No."):
            self.assertNotIn(noise, action)
        remarks = record["remarks"]["text"]
        self.assertIn("airworthiness.A330-A340@airbus.com", remarks)
        self.assertNotIn("SHOULD NOT BE IN REMARKS", remarks)

    def test_current_format_still_extracts(self) -> None:
        record, detail = extract_local_record(self.row(SAMPLE, "2026-0123R1"), SCHEMA)
        self.assertEqual("content-local-v2.1.5", detail["parser_version"])
        self.assertEqual("Airbus S.A.S.", record["ad_identity"]["design_approval_holder"])
        self.assertEqual(["A320-214", "A320-216"], record["publication"]["type_model_designations"])
        self.assertEqual(["2025-0001"], record["supersedure"]["superseded_ad_numbers"])

    def test_legacy_multiline_action_and_form110_furniture(self) -> None:
        record, _ = extract_local_record(self.row(LEGACY_2009_0141, "2009-0141"), SCHEMA)
        self.assertEqual("2009-07-02", record["publication"]["issue_date"])
        self.assertEqual("Airbus (formerly Airbus Industrie)", record["ad_identity"]["design_approval_holder"])
        self.assertIn("Affected rudders", record["definitions"]["text"])
        self.assertIn("(2) Report", record["required_actions"][0]["action"])
        joined = json.dumps(record)
        self.assertNotIn("EASA Form 110", joined)
        self.assertNotIn("SUPERSEDED", joined)
        self.assertNotIn("EASA AD No.", record["required_actions"][0]["action"])

    def test_legacy_subject_tcds_and_action_are_complete(self) -> None:
        record, _ = extract_local_record(self.row(LEGACY_2009_0171, "2009-0171"), SCHEMA)
        self.assertIn("Fire Protection / Hydraulic Power", record["publication"]["subject"])
        self.assertEqual({"26", "29"}, {x["code"] for x in record["publication"]["ata_chapters"]})
        self.assertTrue(any("France" in value for value in record["publication"]["tcds_numbers"]))
        self.assertIn("Replace affected valves", record["required_actions"][0]["action"])

    def test_dah_does_not_fall_through_into_model_text(self) -> None:
        record, _ = extract_local_record(self.row(MODERN_COLLAPSED, "2008-0012"), SCHEMA)
        self.assertEqual("Airbus", record["ad_identity"]["design_approval_holder"])
        self.assertNotIn("Type/Model", record["ad_identity"]["design_approval_holder"])
        self.assertIn("A330", record["publication"]["type_model_designation_text"])

    def test_reference_identifiers_and_direct_original_supersedure(self) -> None:
        record, _ = extract_local_record(self.row(REFERENCE_RICH, "2015-0135R3"), SCHEMA)
        refs = {item.get("number") for item in record["referenced_publications"] if item.get("number")}
        for expected in {"A320-27-1243", "A320-27-1244", "A320-34-1415", "OIT999.0015/15", "C16291A-34-007", "AFMA320TR502"}:
            self.assertIn(expected, refs)
        self.assertEqual(["2015-0087"], record["supersedure"]["superseded_ad_numbers"])

    def test_model_parser_ignores_publication_suffix(self) -> None:
        text = "Applicability: A350-941 aeroplanes modified by Airbus SB A350-52-P012."
        cleaned = _clean_layout_text(text)
        self.assertIn("A350-52-P012", cleaned)

if __name__ == "__main__":
    unittest.main()
