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
                evidence_id="EV1",
                ad_number="2020-0001",
                source_pdf="2020-0001.pdf",
                page_start=2,
                page_end=2,
                section="Required Action(s) and Compliance Time(s)",
                text="Inspect within 500 flight cycles after the effective date.",
                chunk_id="chunk-1",
                rank=1,
            )
        ]

    def answer_payload(self):
        return {
            "status": "answered",
            "answer": "Inspect within 500 flight cycles after the effective date.",
            "conditions": [],
            "compliance_time": ["within 500 flight cycles after the effective date"],
            "exceptions": [],
            "evidence_ids": ["EV1"],
            "reason_for_abstention": None,
        }

    def test_prompt_contains_stable_evidence_id_and_metadata(self):
        prompt = build_user_prompt("When is the inspection required?", self.evidence)
        self.assertIn("[EV1]", prompt)
        self.assertIn("AD: 2020-0001", prompt)
        self.assertIn("Page range: 2-2", prompt)

    def test_resolves_citations_from_evidence_not_model_page_numbers(self):
        result = validate_and_resolve_answer(self.answer_payload(), self.evidence)
        self.assertEqual(result["citations"][0]["page_start"], 2)
        self.assertEqual(result["citations"][0]["ad_number"], "2020-0001")
        self.assertEqual(result["citations"][0]["chunk_id"], "chunk-1")

    def test_unknown_evidence_id_is_rejected(self):
        payload = self.answer_payload()
        payload["evidence_ids"] = ["EV99"]
        with self.assertRaisesRegex(ValueError, "unknown evidence IDs"):
            validate_and_resolve_answer(payload, self.evidence)

    def test_answer_without_evidence_is_rejected_by_contract(self):
        payload = self.answer_payload()
        payload["evidence_ids"] = []
        with self.assertRaisesRegex(ValueError, "response contract"):
            validate_and_resolve_answer(payload, self.evidence)

    def test_insufficient_evidence_requires_reason(self):
        payload = {
            "status": "insufficient_evidence",
            "answer": "The supplied evidence does not establish the requested interval.",
            "conditions": [],
            "compliance_time": [],
            "exceptions": [],
            "evidence_ids": [],
            "reason_for_abstention": "The required compliance paragraph was not supplied.",
        }
        result = validate_and_resolve_answer(payload, [])
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(result["citations"], [])

    def test_conflicting_evidence_can_cite_conflicting_sources(self):
        payload = {
            "status": "conflicting_evidence",
            "answer": "The supplied evidence contains conflicting timing statements.",
            "conditions": [],
            "compliance_time": [],
            "exceptions": [],
            "evidence_ids": ["EV1"],
            "reason_for_abstention": "The supplied passages cannot be reconciled from the available context.",
        }
        result = validate_and_resolve_answer(payload, self.evidence)
        self.assertEqual(result["status"], "conflicting_evidence")
        self.assertEqual(result["citations"][0]["evidence_id"], "EV1")


if __name__ == "__main__":
    unittest.main()
