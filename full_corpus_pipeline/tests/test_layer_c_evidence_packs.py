import tempfile
import unittest
from pathlib import Path

from full_corpus_pipeline.build_layer_c_evidence_packs import build_evidence_pack


class LayerCEvidencePackTests(unittest.TestCase):
    def setUp(self):
        self.chunk_map = {
            "chunk-a": {
                "chunk_id": "chunk-a",
                "file_instance_id": "file-a",
                "ad_number": "2020-0001",
                "source_pdf": "2020-0001.pdf",
                "page_start": 2,
                "page_end": 2,
                "section": "Required Action(s) and Compliance Time(s)",
                "text": "Inspect within 500 flight cycles after the effective date.",
                "lifecycle_status": "latest",
            },
            "chunk-b": {
                "chunk_id": "chunk-b",
                "file_instance_id": "file-b",
                "ad_number": "2021-0002",
                "source_pdf": "2021-0002.pdf",
                "page_start": 3,
                "page_end": 3,
                "section": "Applicability",
                "text": "This AD applies to the listed aeroplane models.",
                "lifecycle_status": "latest",
            },
        }
        self.retrieval_row = {
            "question_id": "E5D-TEST",
            "rank_at_20": 1,
            "source_rank_at_20": 1,
            "retrieved": [
                {
                    "rank": 1,
                    "chunk_id": "chunk-a",
                    "ad_number": "2020-0001",
                    "page_start": 2,
                    "page_end": 2,
                    "section": "Required Action(s) and Compliance Time(s)",
                },
                {
                    "rank": 2,
                    "chunk_id": "chunk-b",
                    "ad_number": "2021-0002",
                    "page_start": 3,
                    "page_end": 3,
                    "section": "Applicability",
                },
            ],
        }
        self.benchmark_row = {
            "question_id": "E5D-TEST",
            "question": "When is the inspection required?",
            "category": "required_action_compliance",
            "query_mode": "known_document",
            "answerable_from_ad": True,
            "target_ad_number": "2020-0001",
            "reference_pages": [2],
        }

    def test_restores_passage_text_and_source_pdf_from_frozen_chunk_store(self):
        pack = build_evidence_pack(
            self.retrieval_row,
            self.benchmark_row,
            chunk_map=self.chunk_map,
        )
        evidence = pack["prompt_payload"]["evidence"]
        self.assertEqual(evidence[0]["evidence_id"], "EV1")
        self.assertEqual(evidence[0]["source_pdf"], "2020-0001.pdf")
        self.assertIn("500 flight cycles", evidence[0]["text"])
        self.assertEqual(evidence[1]["evidence_id"], "EV2")

    def test_prompt_payload_does_not_leak_evaluation_labels(self):
        pack = build_evidence_pack(
            self.retrieval_row,
            self.benchmark_row,
            chunk_map=self.chunk_map,
        )
        payload = pack["prompt_payload"]
        self.assertEqual(set(payload), {"question_id", "question", "evidence"})
        self.assertNotIn("answerable_from_ad", payload)
        self.assertNotIn("target_ad_number", payload)
        self.assertNotIn("reference_pages", payload)
        self.assertNotIn("query_mode", payload)
        self.assertNotIn("category", payload)

    def test_evaluation_metadata_remains_available_outside_prompt(self):
        pack = build_evidence_pack(
            self.retrieval_row,
            self.benchmark_row,
            chunk_map=self.chunk_map,
        )
        metadata = pack["evaluation_metadata"]
        self.assertEqual(metadata["target_ad_number"], "2020-0001")
        self.assertEqual(metadata["reference_pages"], [2])
        self.assertTrue(metadata["answerable_from_ad"])

    def test_prompt_payload_hash_is_deterministic(self):
        first = build_evidence_pack(
            self.retrieval_row,
            self.benchmark_row,
            chunk_map=self.chunk_map,
        )
        second = build_evidence_pack(
            self.retrieval_row,
            self.benchmark_row,
            chunk_map=self.chunk_map,
        )
        self.assertEqual(first["prompt_payload_sha256"], second["prompt_payload_sha256"])

    def test_metadata_drift_is_rejected(self):
        bad = dict(self.retrieval_row)
        bad["retrieved"] = [dict(self.retrieval_row["retrieved"][0])]
        bad["retrieved"][0]["page_start"] = 99
        with self.assertRaisesRegex(ValueError, "metadata mismatch"):
            build_evidence_pack(bad, self.benchmark_row, chunk_map=self.chunk_map)


if __name__ == "__main__":
    unittest.main()
