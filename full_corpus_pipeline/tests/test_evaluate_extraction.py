from __future__ import annotations

import unittest

from full_corpus_pipeline.evaluate_extraction import (
    COMPARABLE_FIELDS,
    legacy_projection_overlap,
    source_contains,
)


class EvaluateExtractionTests(unittest.TestCase):
    def test_primary_fields_ignore_raw_representation_difference(self) -> None:
        gold = {
            "ad_identity": {
                "ad_number": "2025-0058R1",
                "authority": "EASA",
                "document_type": "airworthiness_directive",
                "revision": "R1",
                "design_approval_holder": "Airbus S.A.S.",
            },
            "publication": {
                "subject": "ATA 05 – Time Limits / Maintenance Checks",
                "issue_date": "2025-03-19",
                "effective_date": "2025-03-31",
                "ata_chapters": [{"code": "05"}],
                "manufacturers": ["Manufacturer(s): Airbus"],
                "type_model_designations": ["A340-211 aeroplanes"],
                "tcds_numbers": ["France No. 145 and EASA.A.015"],
                "foreign_ad": "Foreign AD: Not applicable",
            },
            "definitions": {"text": "AMP: reviewed definition"},
            "required_actions": [{"paragraph": "(1)", "action": "reviewed action"}],
        }
        prediction = {
            "ad_identity": {
                "ad_number": "2025-0058R1",
                "authority": "EASA",
                "document_type": "Airworthiness Directive",
                "revision": "R1",
                "design_approval_holder": "AIRBUS S.A.S.",
                "revision_statement": "This AD revises EASA AD 2025-0058.",
            },
            "publication": {
                "subject": "Time Limits / Maintenance Checks",
                "issue_date": "2025-03-19",
                "effective_date": "2025-03-31",
                "ata_chapters": [{"code": "05"}],
                "manufacturers": ["Airbus"],
                "type_model_designations": ["A340-211"],
                "type_model_designation_text": "A340 aeroplanes",
                "tcds_numbers": ["EASA.A.015"],
                "foreign_ad": "Not applicable",
            },
            "definitions": {
                "text": (
                    "AMP: reviewed definition. New and/or more restrictive tasks: "
                    "complete source definition."
                )
            },
            "required_actions": [
                {
                    "action": (
                        "Required as indicated by this AD, unless already accomplished: "
                        "(1) reviewed action. (2) additional complete source wording."
                    )
                }
            ],
        }

        for name, extractor in COMPARABLE_FIELDS.items():
            self.assertEqual(
                extractor(gold),
                extractor(prediction),
                msg=f"primary comparable field changed: {name}",
            )

        self.assertLess(legacy_projection_overlap(prediction, gold)["f1"], 1.0)

    def test_model_identifier_normalization_handles_gold_phrases(self) -> None:
        gold = {
            "publication": {
                "type_model_designations": ["A300 and A300-600 aeroplanes"]
            }
        }
        prediction = {
            "publication": {"type_model_designations": ["A300", "A300-600"]}
        }
        self.assertEqual(
            COMPARABLE_FIELDS["publication_model_identifiers"](gold),
            COMPARABLE_FIELDS["publication_model_identifiers"](prediction),
        )

    def test_source_containment_removes_page_furniture(self) -> None:
        source = """
Definitions:
The AMP means the approved maintenance programme.
Page 1 of 3
TE.CAP.00110-012 © European Union Aviation Safety Agency. All rights reserved.
EASA AD No.: 2025-0058R1
New and/or more restrictive tasks means all new tasks.
"""
        extracted = [
            "The AMP means the approved maintenance programme. "
            "New and/or more restrictive tasks means all new tasks."
        ]
        self.assertTrue(source_contains(extracted, source))


if __name__ == "__main__":
    unittest.main()
