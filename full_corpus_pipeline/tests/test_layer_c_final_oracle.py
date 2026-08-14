from __future__ import annotations

import json
import unittest

from full_corpus_pipeline.layer_c.build_final_oracle_evidence_packs import (
    FINAL_ORACLE_EVIDENCE_PACK_VERSION,
    build_final_oracle_pack,
)


class FinalOracleEvidenceTests(unittest.TestCase):
    def test_answerable_pack_uses_reference_source_without_answer_leakage(self) -> None:
        question = {
            "question_id": "E5F-999",
            "question": "What action is required?",
            "answerable_from_ad": True,
            "target_ad_number": "2026-0001",
            "reference_pages": [2],
            "reference_sections": ["Required Action(s) and Compliance Time(s)"],
            "reference_answer": "SECRET GOLD ANSWER",
            "category": "required_action_compliance",
            "query_mode": "known_document",
        }
        chunks = [
            {
                "chunk_id": "target",
                "ad_number": "2026-0001",
                "source_pdf": "target.pdf",
                "page_start": 2,
                "page_end": 2,
                "section": "Required Action(s) and Compliance Time(s)",
                "text": "Perform the required inspection within 100 flight cycles.",
            },
            {
                "chunk_id": "distractor",
                "ad_number": "2026-0002",
                "source_pdf": "other.pdf",
                "page_start": 2,
                "page_end": 2,
                "section": "Required Action(s) and Compliance Time(s)",
                "text": "Wrong document.",
            },
        ]
        retrieved_pack = {
            "prompt_payload": {
                "question_id": "E5F-999",
                "question": question["question"],
                "evidence": [{"evidence_id": "EV1", "text": "primary evidence"}],
            }
        }
        pack = build_final_oracle_pack(
            question,
            chunks=chunks,
            retrieved_pack=retrieved_pack,
            retrieval_row={"rank_at_20": 4, "source_rank_at_20": 2},
            final_questions_sha256="abc123",
        )

        self.assertEqual(pack["evidence_pack_version"], FINAL_ORACLE_EVIDENCE_PACK_VERSION)
        self.assertEqual(pack["evidence_condition"], "oracle_reference_evidence")
        self.assertEqual(pack["final_questions_sha256"], "abc123")
        self.assertEqual(set(pack["prompt_payload"]), {"question_id", "question", "evidence"})
        self.assertEqual(pack["prompt_payload"]["evidence"][0]["chunk_id"], "target")
        rendered = json.dumps(pack["prompt_payload"], sort_keys=True)
        self.assertNotIn("SECRET GOLD ANSWER", rendered)
        self.assertNotIn("reference_answer", rendered)
        self.assertNotIn("target_ad_number", rendered)
        self.assertNotIn("reference_pages", rendered)
        self.assertNotIn("category", rendered)
        self.assertNotIn("query_mode", rendered)

    def test_negative_pack_preserves_primary_prompt_evidence(self) -> None:
        question = {
            "question_id": "E5F-998",
            "question": "Give unavailable repair geometry.",
            "answerable_from_ad": False,
            "target_ad_number": "2026-0003",
            "reference_pages": [],
            "reference_sections": [],
            "reference_answer": "The AD does not contain it.",
            "category": "insufficient_conflict_abstention",
            "query_mode": "abstention_conflict",
        }
        evidence = [
            {
                "evidence_id": "EV1",
                "rank": 1,
                "chunk_id": "neg",
                "ad_number": "2026-0003",
                "source_pdf": "neg.pdf",
                "page_start": 2,
                "page_end": 2,
                "section": "Required Action(s)",
                "text": "Contact Airbus for approved instructions.",
            }
        ]
        pack = build_final_oracle_pack(
            question,
            chunks=[],
            retrieved_pack={
                "prompt_payload": {
                    "question_id": "E5F-998",
                    "question": question["question"],
                    "evidence": evidence,
                }
            },
            retrieval_row={"rank_at_20": None, "source_rank_at_20": None},
            final_questions_sha256="def456",
        )
        self.assertEqual(pack["evidence_source"], "primary_frozen_top5_negative_control")
        self.assertEqual(pack["prompt_payload"]["evidence"], evidence)
        self.assertEqual(pack["evidence_depth"], 1)


if __name__ == "__main__":
    unittest.main()
