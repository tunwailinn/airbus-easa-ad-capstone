from __future__ import annotations

import unittest

from full_corpus_pipeline.layer_c.build_oracle_evidence_packs import (
    ORACLE_EVIDENCE_PACK_VERSION,
    build_oracle_pack,
    select_answerable_oracle_chunks,
)


class LayerCOracleEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.chunks = [
            {
                "chunk_id": "wrong-ad",
                "ad_number": "2099-9999",
                "source_pdf": "wrong.pdf",
                "page_start": 2,
                "page_end": 2,
                "section": "Compliance",
                "text": "Distractor with the same timing phrase.",
            },
            {
                "chunk_id": "target-document",
                "ad_number": "2020-0001",
                "source_pdf": "target.pdf",
                "page_start": 1,
                "page_end": 2,
                "section": "Document",
                "text": "Target document context.",
            },
            {
                "chunk_id": "target-compliance",
                "ad_number": "2020-0001",
                "source_pdf": "target.pdf",
                "page_start": 2,
                "page_end": 2,
                "section": "Compliance",
                "text": "Perform the target action within 30 days.",
            },
        ]

    def test_answerable_oracle_uses_target_reference_page_and_section(self) -> None:
        question = {
            "question_id": "E5D-001",
            "target_ad_number": "2020-0001",
            "reference_pages": [2],
            "reference_sections": ["Compliance"],
        }
        selected, source_pdf = select_answerable_oracle_chunks(question, self.chunks)
        self.assertEqual(source_pdf, "target.pdf")
        self.assertEqual(selected[0]["chunk_id"], "target-compliance")
        self.assertTrue(all(row["ad_number"] == "2020-0001" for row in selected))
        self.assertNotIn("wrong-ad", {row["chunk_id"] for row in selected})

    def test_oracle_pack_does_not_expose_reference_answer(self) -> None:
        question = {
            "question_id": "E5D-001",
            "question": "What is required?",
            "category": "required_action_compliance",
            "query_mode": "known_document",
            "answerable_from_ad": True,
            "target_ad_number": "2020-0001",
            "reference_pages": [2],
            "reference_sections": ["Compliance"],
            "reference_answer": "SECRET GOLD ANSWER",
        }
        pack = build_oracle_pack(
            question,
            chunks=self.chunks,
            retrieved_pack={"prompt_payload": {"evidence": []}},
            retrieval_row={"rank_at_20": 1, "source_rank_at_20": 1},
        )
        self.assertEqual(pack["evidence_pack_version"], ORACLE_EVIDENCE_PACK_VERSION)
        self.assertEqual(pack["evidence_source"], "oracle_reference_pages")
        rendered_prompt = str(pack["prompt_payload"])
        self.assertNotIn("SECRET GOLD ANSWER", rendered_prompt)
        self.assertNotIn("reference_answer", rendered_prompt)
        self.assertEqual(pack["prompt_payload"]["evidence"][0]["chunk_id"], "target-compliance")

    def test_negative_control_preserves_frozen_evidence(self) -> None:
        question = {
            "question_id": "E5D-055",
            "question": "What exact external procedure is required?",
            "category": "insufficient_conflict_abstention",
            "query_mode": "abstention_conflict",
            "answerable_from_ad": False,
            "reference_pages": [],
            "reference_sections": [],
            "reference_answer": "The AD does not provide the exact procedure.",
        }
        frozen_evidence = [
            {
                "evidence_id": "EV1",
                "rank": 1,
                "chunk_id": "negative",
                "ad_number": "2020-0001",
                "source_pdf": "target.pdf",
                "page_start": 2,
                "page_end": 2,
                "section": "Compliance",
                "text": "Contact the manufacturer for approved instructions.",
            }
        ]
        pack = build_oracle_pack(
            question,
            chunks=self.chunks,
            retrieved_pack={"prompt_payload": {"evidence": frozen_evidence}},
            retrieval_row={"rank_at_20": None, "source_rank_at_20": None},
        )
        self.assertEqual(pack["evidence_source"], "frozen_top5_negative_control")
        self.assertEqual(pack["prompt_payload"]["evidence"], frozen_evidence)
        self.assertNotIn("reference_answer", pack["prompt_payload"])


if __name__ == "__main__":
    unittest.main()
