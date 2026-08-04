from __future__ import annotations

import unittest

from full_corpus_pipeline.evaluate_extraction import (
    COMPARABLE_FIELDS,
    STABLE_METADATA_FIELDS,
    benchmark_scope_status,
    contamination,
    legacy_projection_overlap,
    source_contains,
    source_has_section,
)


class EvaluateExtractionTests(unittest.TestCase):
    def test_scope_filter_distinguishes_out_of_scope_from_parser_garbage(self) -> None:
        for holder in (
            "Airbus",
            "Airbus S.A.S.",
            "AIRBUS INDUSTRIE",
            "Airbus (formerly Airbus Industrie)",
        ):
            status, _ = benchmark_scope_status(
                {"ad_identity": {"design_approval_holder": holder}}
            )
            self.assertEqual("eligible", status)

        for holder in ("LUFTHANSA TECHNIK AG", "Airbus Defence and Space S.A."):
            status, _ = benchmark_scope_status(
                {"ad_identity": {"design_approval_holder": holder}}
            )
            self.assertEqual("excluded", status)

        status, _ = benchmark_scope_status(
            {
                "ad_identity": {
                    "design_approval_holder": (
                        "Type/Model designations Airbus S.A.S. A310 aircraft"
                    )
                }
            }
        )
        self.assertEqual("unknown", status)

    def test_source_heading_detects_wrapped_legacy_action(self) -> None:
        source = """
Reason:
Unsafe condition.
Required Action(s)
and Compliance
Time(s):
Inspect.
Ref. Publications:
Airbus SB A320-55A1038.
"""
        self.assertTrue(source_has_section(source, "required_actions"))
        self.assertTrue(source_has_section(source, "referenced_publications_text"))

    def test_contamination_does_not_flag_normal_supersedure_prose(self) -> None:
        self.assertNotIn(
            "status_watermark",
            contamination(["This AD supersedes an AD which is superseded."]),
        )
        self.assertIn("status_watermark", contamination(["SUPERSEDED"]))
        self.assertIn("page_number", contamination(["EASA Form 110 Page 2/8"]))

    def test_source_containment_removes_legacy_page_furniture(self) -> None:
        source = """
Required Action(s)
and Compliance
Time(s):
Inspect the rudder.
EASA Form 110 Page 2/8
EASA AD No.: 2009-0141
Report results.
"""
        self.assertTrue(source_contains(["Inspect the rudder. Report results."], source))

    def test_publication_models_are_secondary_not_stable(self) -> None:
        self.assertIn("publication_model_identifiers", COMPARABLE_FIELDS)
        self.assertNotIn("publication_model_identifiers", STABLE_METADATA_FIELDS)

    def test_legacy_projection_remains_diagnostic(self) -> None:
        gold = {
            "ad_identity": {"ad_number": "2020-0016"},
            "definitions": {"text": "semantic"},
        }
        prediction = {
            "ad_identity": {"ad_number": "2020-0016"},
            "definitions": {"text": "complete raw source text"},
        }
        self.assertLessEqual(legacy_projection_overlap(prediction, gold)["f1"], 1.0)


if __name__ == "__main__":
    unittest.main()
