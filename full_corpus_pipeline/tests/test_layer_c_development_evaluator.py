from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from full_corpus_pipeline.layer_c.evaluate_development import main, pages_overlap


class LayerCDevelopmentEvaluatorTests(unittest.TestCase):
    def test_pages_overlap(self) -> None:
        self.assertTrue(pages_overlap({"page_start": 2, "page_end": 3}, [3]))
        self.assertFalse(pages_overlap({"page_start": 2, "page_end": 3}, [4]))

    def test_partial_run_builds_automatic_and_human_review_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_value:
            root = Path(temp_value)
            run_dir = root / "run"
            output_dir = root / "evaluation"
            run_dir.mkdir()

            questions_path = root / "development_questions.jsonl"
            questions = [
                {
                    "question_id": "E5D-001",
                    "split": "development",
                    "base_ad_number": "2000-0001",
                    "target_ad_number": "2000-0001",
                    "category": "required_action_compliance",
                    "query_mode": "known_document",
                    "question": "What does AD 2000-0001 require?",
                    "answerable_from_ad": True,
                    "reference_pages": [2],
                    "reference_sections": ["Compliance"],
                    "reference_answer": "Do the required action.",
                    "required_conditions": [],
                    "required_exceptions": [],
                    "review_status": "human_verified",
                },
                {
                    "question_id": "E5D-002",
                    "split": "development",
                    "base_ad_number": "2000-0002",
                    "category": "insufficient_conflict_abstention",
                    "query_mode": "abstention_conflict",
                    "question": "Can this be determined?",
                    "answerable_from_ad": False,
                    "reference_pages": [],
                    "reference_sections": [],
                    "reference_answer": "Evidence is insufficient.",
                    "review_status": "human_verified",
                },
            ]
            questions_path.write_text(
                "".join(json.dumps(row) + "\n" for row in questions), encoding="utf-8"
            )
            benchmark_sha = hashlib.sha256(questions_path.read_bytes()).hexdigest()

            retrieval_path = root / "e5d.json"
            retrieval_path.write_text(
                json.dumps(
                    {
                        "benchmark_sha256": benchmark_sha,
                        "questions": [
                            {"question_id": "E5D-001", "rank_at_20": 2},
                            {"question_id": "E5D-002", "rank_at_20": None},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "run_manifest.json").write_text(
                json.dumps(
                    {
                        "scope": "E5 development only",
                        "run_id": "smoke",
                        "provider": "deepseek",
                        "model": "deepseek-v4-pro",
                        "reasoning_effort": "high",
                        "selected_question_count": 2,
                    }
                ),
                encoding="utf-8",
            )
            responses = [
                {
                    "question_id": "E5D-001",
                    "answer": {
                        "status": "answered",
                        "answer": "Do the required action.",
                        "conditions": [],
                        "compliance_time": [],
                        "exceptions": [],
                        "citations": [
                            {
                                "ad_number": "2000-0001",
                                "page_start": 2,
                                "page_end": 2,
                                "evidence_id": "EV1",
                            }
                        ],
                    },
                },
                {
                    "question_id": "E5D-002",
                    "answer": {
                        "status": "insufficient_evidence",
                        "answer": None,
                        "conditions": [],
                        "compliance_time": [],
                        "exceptions": [],
                        "citations": [],
                        "reason_for_abstention": "Missing evidence.",
                    },
                },
            ]
            (run_dir / "responses.jsonl").write_text(
                "".join(json.dumps(row) + "\n" for row in responses), encoding="utf-8"
            )
            (run_dir / "failures.jsonl").write_text("", encoding="utf-8")

            argv = [
                "evaluate_development",
                "--run-dir",
                str(run_dir),
                "--questions",
                str(questions_path),
                "--retrieval-report",
                str(retrieval_path),
                "--output-dir",
                str(output_dir),
            ]
            with patch.object(sys, "argv", argv):
                self.assertEqual(main(), 0)

            report = json.loads((output_dir / "automatic_evaluation.json").read_text(encoding="utf-8"))
            self.assertEqual(report["success_count"], 2)
            self.assertEqual(report["failure_count"], 0)
            self.assertEqual(report["answerability_status_accuracy"], 1.0)
            self.assertEqual(report["reference_page_citation_hit_rate"], 1.0)
            self.assertEqual(report["target_ad_citation_hit_rate"], 1.0)
            self.assertTrue((output_dir / "human_review.csv").exists())
            self.assertTrue((output_dir / "review_packet.md").exists())


if __name__ == "__main__":
    unittest.main()
