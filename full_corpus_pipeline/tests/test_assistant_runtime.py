from __future__ import annotations

import unittest

from full_corpus_pipeline.assistant.cli import render_human
from full_corpus_pipeline.assistant.runtime import build_live_evidence


class AssistantRuntimeTests(unittest.TestCase):
    def test_build_live_evidence_preserves_top_ranked_source_metadata(self) -> None:
        reranked = [
            {
                "chunk_id": "chunk-a",
                "ad_number": "2011-0041R1",
                "source_pdf": "example.pdf",
                "page_start": 2,
                "page_end": 2,
                "section": "Required Action(s) and Compliance Time(s)",
                "text": "Required action text.",
                "reranker_score": 7.0,
                "pre_rerank_rank": 3,
            },
            {
                "chunk_id": "chunk-b",
                "ad_number": "2011-0041R1",
                "source_pdf": "example.pdf",
                "page_start": 1,
                "page_end": 1,
                "section": "Document",
                "text": "Document text.",
                "reranker_score": 4.0,
                "pre_rerank_rank": 1,
            },
        ]

        evidence, rows = build_live_evidence(reranked, depth=1)

        self.assertEqual(len(evidence), 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["evidence_id"], "EV1")
        self.assertEqual(rows[0]["chunk_id"], "chunk-a")
        self.assertEqual(rows[0]["page_start"], 2)
        self.assertEqual(evidence[0].ad_number, "2011-0041R1")
        self.assertEqual(evidence[0].section, "Required Action(s) and Compliance Time(s)")

    def test_build_live_evidence_rejects_zero_depth(self) -> None:
        with self.assertRaises(ValueError):
            build_live_evidence([], depth=0)

    def test_cli_renderer_shows_citations_and_safety_boundary(self) -> None:
        result = {
            "status": "answered",
            "route": {"mode": "known_document"},
            "answer": "Do the required inspection.",
            "conditions": [],
            "compliance_time": ["Within 500 FC."],
            "exceptions": [],
            "reason_for_abstention": None,
            "citations": [
                {
                    "evidence_id": "EV1",
                    "ad_number": "2008-0008",
                    "page_start": 2,
                    "page_end": 2,
                    "section": "Required Action(s) and Compliance Time(s)",
                }
            ],
            "retrieval": {"evidence": []},
            "safety": {
                "source_authority": "Original EASA AD passages remain authoritative.",
                "decision_boundary": "No aircraft-specific legal compliance determination.",
            },
        }

        rendered = render_human(result, show_evidence=False)
        self.assertIn("Status: answered", rendered)
        self.assertIn("2008-0008 | p.2", rendered)
        self.assertIn("Safety boundary:", rendered)
        self.assertIn("No aircraft-specific legal compliance determination.", rendered)


if __name__ == "__main__":
    unittest.main()
