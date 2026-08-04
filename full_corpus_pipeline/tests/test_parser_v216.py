from __future__ import annotations

import json
import unittest
from pathlib import Path

from full_corpus_pipeline.local_extractor_v216 import (
    PARSER_VERSION,
    _flexible_a300_models,
    _header_subject_and_ata,
    _normalize_header_layout,
    _postprocess_supersedure,
    extract_local_record,
)
from full_corpus_pipeline.scope_policy import classify_holder


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads(
    (ROOT / "full_corpus_pipeline/content_record.schema.json").read_text(encoding="utf-8")
)


class ParserV216Tests(unittest.TestCase):
    def test_doubled_colon_dah_is_recovered(self) -> None:
        text = """
EASA AD No.: 2020-0016
Airworthiness Directive
AD No.: 2020-0016
Issued: 30 January 2020
Design Approval Holder’s Name::
AIRBUS
Type/Model designation(s):
A380 aeroplanes
Effective Date: 13 February 2020
TCDS Number(s): EASA.A.110
Foreign AD: Not applicable
Supersedure: None
ATA 36 – Pneumatic – Engine Bleed Air Supply System – Modification
Manufacturer(s): Airbus
Applicability: A380-841 and A380-842 aeroplanes.
Reason: A source-grounded reason.
Required Action(s) and Compliance Time(s):
Modify the affected aeroplanes.
Ref. Publications:
Airbus Service Bulletin A380-36-8001.
Remarks:
AMOC approval remains with EASA.
"""
        record, detail = extract_local_record(
            {
                "text": text,
                "ad_number": "2020-0016",
                "is_emergency": False,
                "correction_date": "",
                "issue_date": "",
            },
            SCHEMA,
        )
        self.assertEqual("AIRBUS", record["ad_identity"]["design_approval_holder"])
        self.assertEqual(PARSER_VERSION, detail["parser_version"])

    def test_legacy_type_holder_and_plural_designations_are_normalized(self) -> None:
        source = """
Type Approval Holder’s Name :
AIRBUS
Type/Model designations:
A310, A300-600 and A300-600ST aircraft
"""
        normalized = _normalize_header_layout(source)
        self.assertIn("Design Approval Holder’s Name:", normalized)
        self.assertIn("Type/Model designation(s):", normalized)

    def test_multi_holder_heading_is_preserved_for_scope_policy(self) -> None:
        source = """
Type Approval Holders names:
Airbus
ATR-GIE Avions de Transport Regional
BAE Systems
Type/Model designations:
A320 aircraft
"""
        normalized = _normalize_header_layout(source)
        self.assertIn("Design Approval Holder’s Name:", normalized)
        status, _, _ = classify_holder("Airbus ATR-GIE Avions de Transport Regional BAE Systems")
        self.assertEqual("excluded", status)

    def test_multi_ata_subject_keeps_both_blocks(self) -> None:
        text = """
Foreign AD: Not applicable
Supersedure: This AD revises EASA AD 2023-0093 dated 05 May 2023, which superseded EASA AD 2022-0032R1 dated 29 July 2022.
ATA 32 – Landing Gear – Braking and Steering Control Unit – Replacement /
Master Minimum Equipment List – Amendment
ATA 92 – Electric and Electronic Common Installation – Relays – Replacement
Manufacturer(s): Airbus S.A.S.
Applicability: A319, A320 and A321 aeroplanes.
"""
        subject, chapters = _header_subject_and_ata(text)
        self.assertIn("Landing Gear", subject or "")
        self.assertIn("ATA 92", subject or "")
        self.assertEqual(["32", "92"], [item["code"] for item in chapters])

    def test_revision_chain_is_not_false_direct_supersedure(self) -> None:
        record = {
            "supersedure": {
                "statement": (
                    "This AD revises EASA AD 2023-0093 dated 05 May 2023, "
                    "which superseded EASA AD 2022-0032R1 dated 29 July 2022."
                ),
                "superseded_ad_numbers": ["2023-0093", "2022-0032R1"],
            }
        }
        _postprocess_supersedure(record)
        self.assertNotIn("superseded_ad_numbers", record["supersedure"])

    def test_flexible_a300_variants(self) -> None:
        models = _flexible_a300_models(
            "A300-B4-601, A300B4-603, A300-C4-605R and A300-600ST aeroplanes"
        )
        self.assertEqual(
            ["A300B4-601", "A300B4-603", "A300C4-605R", "A300-600ST"],
            models,
        )

    def test_scope_aliases_external_and_unknown_are_separate(self) -> None:
        for holder in (
            "Airbus",
            "Airbus S.A.S.",
            "Airbus Airbus Industrie",
            "Airbus SAS Airbus Industries",
        ):
            self.assertEqual("eligible", classify_holder(holder)[0])
        self.assertEqual("excluded", classify_holder("Lufthansa Technik AG")[0])
        self.assertEqual("excluded", classify_holder("Airbus / BAE Systems")[0])
        self.assertEqual("unknown", classify_holder(None)[0])
        self.assertEqual(
            "unknown",
            classify_holder("Airbus A300-600 aircraft all certified models and serial numbers")[0],
        )


if __name__ == "__main__":
    unittest.main()
