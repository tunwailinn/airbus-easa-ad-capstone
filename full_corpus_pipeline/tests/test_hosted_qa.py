import unittest

from full_corpus_pipeline.hosted_qa import (
    Evidence,
    build_user_prompt,
    validate_and_resolve_answer,
)


class HostedQATests(unittest.TestCase):
    def setUp(self):
        self.evidence = [
            Evidence(
                evidence_id="E1",
                ad_number="2020-0001",
                source_pdf="2020-0001.pdf",
                page_start=2,
                page_end=2,
                section="Required Action(s) and Compliance Time(s)",
                text="Inspect within 500 flight cycles after the effective date.",
            )
        ]

    def test_prompt_contains_stable_evidence_id_and_metadata(self):
        prompt = build_user_prompt("When is the inspection required?", self.evidence)
        self.assertIn("[E1]", prompt)
        self.assertIn("AD: 2020-0001", prompt)
        self.assertIn("Page range: 2-2", prompt)

    def test_resolves_citations_from_evidence_not_model_page_numbers(self):
        result = validate_and_resolve_answer(
            {
                "status": "answer",
                "answer": "Within 500 flight cycles after the effective date.",
                "conditions": [],
                "compliance_time": ["within 500 flight cycles"],
                "exceptions": [],
                "evidence_ids": ["E1"],
            },
            self.evidence,
        )
        self.assertEqual(result["citations"][0]["page_start"], 2)
        self.assertEqual(result["citations"][0]["ad_number"], "2020-0001")

    def test_unknown_evidence_id_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown evidence IDs"):
            validate_and_resolve_answer(
                {
                    "status": "answer",
                    "answer": "unsupported",
                    "conditions": [],
                    "compliance_time": [],
                    "exceptions": [],
                    "evidence_ids": ["E99"],
                },
                self.evidence,
            )

    def test_answer_without_evidence_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "cite at least one"):
            validate_and_resolve_answer(
                {
                    "status": "answer",
                    "answer": "unsupported",
                    "conditions": [],
                    "compliance_time": [],
                    "exceptions": [],
                    "evidence_ids": [],
                },
                self.evidence,
            )

    def test_abstention_can_have_no_evidence(self):
        result = validate_and_resolve_answer(
            {
                "status": "abstain",
                "answer": "The supplied evidence does not establish this.",
                "conditions": [],
                "compliance_time": [],
                "exceptions": [],
                "evidence_ids": [],
            },
            [],
        )
        self.assertEqual(result["status"], "abstain")
        self.assertEqual(result["citations"], [])


if __name__ == "__main__":
    unittest.main()
