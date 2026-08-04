import json
import tempfile
import unittest
from pathlib import Path

from full_corpus_pipeline.evaluate_retrieval_experiments import (
    EXPECTED_BUILD_VERSION,
    RERANKER_DEVICE,
    paired_comparison,
    relevance_rank,
    share_dense_query_encoder,
    source_rank,
    summarize,
    validate_build_summary,
)


class RetrievalExperimentEvaluationTests(unittest.TestCase):
    def test_source_and_page_rank(self):
        question = {
            "target_ad_number": "2026-0001",
            "reference_pages": [2],
        }
        results = [
            {
                "ad_number": "2026-0001",
                "page_start": 1,
                "page_end": 1,
            },
            {
                "ad_number": "2026-0001",
                "page_start": 2,
                "page_end": 2,
            },
        ]
        self.assertEqual(source_rank(results, question), 1)
        self.assertEqual(relevance_rank(results, question), 2)

    def test_summary_metrics(self):
        rows = [
            {"rank": 1, "source_rank": 1},
            {"rank": 3, "source_rank": 2},
            {"rank": None, "source_rank": None},
        ]
        metrics = summarize(rows)
        self.assertAlmostEqual(metrics["recall_at_1"], 1 / 3)
        self.assertAlmostEqual(metrics["recall_at_3"], 2 / 3)
        self.assertAlmostEqual(metrics["recall_at_5"], 2 / 3)
        self.assertAlmostEqual(metrics["correct_source_at_5"], 2 / 3)
        self.assertAlmostEqual(metrics["correct_source_and_page_at_5"], 2 / 3)

    def test_paired_comparison(self):
        e0 = [
            {"question_id": "Q1", "rank": 3},
            {"question_id": "Q2", "rank": 1},
            {"question_id": "Q3", "rank": None},
        ]
        e4 = [
            {"question_id": "Q1", "rank": 1},
            {"question_id": "Q2", "rank": 2},
            {"question_id": "Q3", "rank": None},
        ]
        result = paired_comparison(e0, e4)
        self.assertEqual(result["e4_better_rank_count"], 1)
        self.assertEqual(result["e0_better_rank_count"], 1)
        self.assertEqual(result["tie_count"], 1)

    def test_build_summary_gate_accepts_only_frozen_v12(self):
        summary = {
            "retrieval_build_version": "rag-index-build-v1.2",
            "document_count": 1786,
            "chunk_size_policy": {
                "count_method": "whitespace_split",
                "e0_max_tokens": 350,
                "e4_max_tokens": 450,
            },
            "experiments": {
                "e0": {"chunk_stats": {"document_count": 1786, "max_tokens": 350}},
                "e4": {"chunk_stats": {"document_count": 1786, "max_tokens": 450}},
            },
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "build_summary.json").write_text(
                json.dumps(summary), encoding="utf-8"
            )
            loaded = validate_build_summary(root)
            self.assertEqual(loaded["retrieval_build_version"], EXPECTED_BUILD_VERSION)

            summary["retrieval_build_version"] = "rag-index-build-v1.1"
            (root / "build_summary.json").write_text(
                json.dumps(summary), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "rag-index-build-v1.2"):
                validate_build_summary(root)

    def test_runtime_policy_shares_dense_encoder_and_pins_reranker_cpu(self):
        class FakeIndex:
            _encoder = None

        e0 = FakeIndex()
        e4 = FakeIndex()
        encoder = object()
        share_dense_query_encoder(e0, e4, encoder)
        self.assertIs(e0._encoder, encoder)
        self.assertIs(e4._encoder, encoder)
        self.assertEqual(RERANKER_DEVICE, "cpu")


if __name__ == "__main__":
    unittest.main()
