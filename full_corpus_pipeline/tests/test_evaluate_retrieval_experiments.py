import json
import tempfile
import unittest
from pathlib import Path

from full_corpus_pipeline.evaluate_retrieval_experiments import (
    EXPECTED_BUILD_VERSION,
    FROZEN_CANDIDATE_LIMIT,
    RERANKER_DEVICE,
    dense_results_from_positions,
    hybrid_candidates_from_dense,
    paired_comparison,
    relevance_rank,
    source_rank,
    summarize,
    validate_build_summary,
)
from full_corpus_pipeline.rerank_candidates_worker import rerank_items
from full_corpus_pipeline.retrieval import Chunk


class RetrievalExperimentEvaluationTests(unittest.TestCase):
    def test_source_and_page_rank(self):
        question = {"target_ad_number": "2026-0001", "reference_pages": [2]}
        results = [
            {"ad_number": "2026-0001", "page_start": 1, "page_end": 1},
            {"ad_number": "2026-0001", "page_start": 2, "page_end": 2},
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
            (root / "build_summary.json").write_text(json.dumps(summary), encoding="utf-8")
            loaded = validate_build_summary(root)
            self.assertEqual(loaded["retrieval_build_version"], EXPECTED_BUILD_VERSION)
            summary["retrieval_build_version"] = "rag-index-build-v1.1"
            (root / "build_summary.json").write_text(json.dumps(summary), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "rag-index-build-v1.2"):
                validate_build_summary(root)

    def test_runtime_policy_keeps_frozen_candidate_limit_and_cpu_reranker(self):
        self.assertEqual(FROZEN_CANDIDATE_LIMIT, 20)
        self.assertEqual(RERANKER_DEVICE, "cpu")

    def test_hybrid_candidates_preserve_frozen_rrf_candidate_union(self):
        first = Chunk(
            chunk_id="a",
            file_instance_id="f1",
            ad_number="2026-0001",
            source_pdf="a.pdf",
            page_start=1,
            page_end=1,
            section="Reason",
            text="hydraulic inspection required",
        )
        second = Chunk(
            chunk_id="b",
            file_instance_id="f2",
            ad_number="2026-0002",
            source_pdf="b.pdf",
            page_start=2,
            page_end=2,
            section="Compliance",
            text="inspection before 500 flight cycles",
        )

        class FakeIndex:
            chunks = [first, second]

            def sparse_search(self, query, limit):
                return [{"chunk_id": "a", "score": 2.0}]

        dense_row = [
            {"index": 1, "score": 0.9},
            {"index": 0, "score": 0.8},
        ]
        candidates = hybrid_candidates_from_dense(
            FakeIndex(),
            "hydraulic inspection",
            dense_row,
            candidate_limit=20,
        )
        by_id = {candidate["chunk_id"]: candidate for candidate in candidates}
        self.assertEqual(set(by_id), {"a", "b"})
        self.assertAlmostEqual(by_id["a"]["retrieval_score"], 1 / 61 + 1 / 62)
        self.assertAlmostEqual(by_id["b"]["retrieval_score"], 1 / 61)

    def test_dense_results_map_faiss_positions_without_changing_rank(self):
        first = Chunk(
            chunk_id="a", file_instance_id="f1", ad_number="A", source_pdf="a.pdf",
            page_start=1, page_end=1, section="Flat", text="first"
        )
        second = Chunk(
            chunk_id="b", file_instance_id="f2", ad_number="B", source_pdf="b.pdf",
            page_start=2, page_end=2, section="Flat", text="second"
        )

        class FakeIndex:
            chunks = [first, second]

        results = dense_results_from_positions(
            FakeIndex(),
            [{"index": 1, "score": 0.9}, {"index": 0, "score": 0.8}],
        )
        self.assertEqual([item["chunk_id"] for item in results], ["b", "a"])
        self.assertEqual([item["score"] for item in results], [0.9, 0.8])

    def test_isolated_worker_reranks_without_retrieval_dependencies(self):
        class FakeModel:
            def predict(self, pairs, show_progress_bar=False, device="cpu"):
                self.last_device = device
                return [0.1, 0.9]

        items = [
            {
                "item_id": "Q1",
                "query": "inspection timing",
                "candidates": [
                    {"chunk_id": "a", "text": "first passage"},
                    {"chunk_id": "b", "text": "second passage"},
                ],
            }
        ]
        model = FakeModel()
        output = rerank_items(items, model, limit=1, device="cpu")
        self.assertEqual(output[0]["results"][0]["chunk_id"], "b")
        self.assertEqual(model.last_device, "cpu")


if __name__ == "__main__":
    unittest.main()
