from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from full_corpus_pipeline.layer_c.run_final_benchmark import (
    EXPECTED_CATEGORY_COUNTS,
    EXPECTED_MODE_COUNTS,
    build_evidence,
    load_final_questions,
)


class LayerCFinalBenchmarkTests(unittest.TestCase):
    def _questions(self) -> list[dict]:
        categories: list[str] = []
        for category, count in EXPECTED_CATEGORY_COUNTS.items():
            categories.extend([category] * count)
        modes: list[str] = []
        for mode, count in EXPECTED_MODE_COUNTS.items():
            modes.extend([mode] * count)
        rows: list[dict] = []
        for index in range(40):
            answerable = index < 36
            rows.append(
                {
                    "question_id": f"E5F-{index + 1:03d}",
                    "split": "final_test",
                    "base_ad_number": f"20{index:02d}-0001",
                    "target_ad_number": f"20{index:02d}-0001" if answerable else None,
                    "category": categories[index],
                    "query_mode": modes[index],
                    "question": f"Synthetic final question {index + 1}?",
                    "answerable_from_ad": answerable,
                    "reference_pages": [1] if answerable else [],
                    "reference_sections": ["Document"] if answerable else [],
                    "reference_answer": "Synthetic answer" if answerable else "Insufficient evidence.",
                    "required_conditions": [],
                    "required_exceptions": [],
                    "review_status": "human_verified",
                }
            )
        return rows

    def test_final_question_contract_accepts_sealed_distribution(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            path = Path(value) / "final_questions.jsonl"
            path.write_text(
                "".join(json.dumps(row) + "\n" for row in self._questions()),
                encoding="utf-8",
            )
            loaded = load_final_questions(path)
            self.assertEqual(len(loaded), 40)
            self.assertEqual(sum(bool(row["answerable_from_ad"]) for row in loaded), 36)

    def test_prompt_pack_excludes_private_reference_fields(self) -> None:
        question = self._questions()[0]
        candidate = {
            "chunk_id": "chunk-1",
            "ad_number": "2000-0001",
            "source_pdf": "source.pdf",
            "page_start": 2,
            "page_end": 2,
            "section": "Compliance",
            "text": "Required action within 30 days.",
        }
        pack = build_evidence(question, [candidate])
        payload = pack["prompt_payload"]
        self.assertEqual(set(payload), {"question_id", "question", "evidence"})
        rendered = json.dumps(payload)
        self.assertNotIn("reference_answer", rendered)
        self.assertNotIn("target_ad_number", rendered)
        self.assertNotIn("reference_pages", rendered)
        self.assertEqual(payload["evidence"][0]["evidence_id"], "EV1")


if __name__ == "__main__":
    unittest.main()
