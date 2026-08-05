import json
import sqlite3
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from full_corpus_pipeline.e5_retrieval import EngineeringAwareRetriever
from full_corpus_pipeline.e5b_retrieval import EvidenceAssemblyRetriever
from full_corpus_pipeline.retrieval import Chunk


class E5BRetrievalTests(unittest.TestCase):
    def _make_index(self, root: Path) -> Path:
        chunks = [
            Chunk(
                chunk_id="target-action",
                file_instance_id="target-file",
                ad_number="2020-0001",
                source_pdf="target.pdf",
                page_start=2,
                page_end=2,
                section="Required Action(s) and Compliance Time(s)",
                text=(
                    "cargo door aft door inspection interval 400 flight cycles "
                    "forward door inspection interval 800 flight cycles"
                ),
                lifecycle_status="operational",
            ),
            Chunk(
                chunk_id="target-ref",
                file_instance_id="target-file",
                ad_number="2020-0001",
                source_pdf="target.pdf",
                page_start=3,
                page_end=3,
                section="Ref. Publications",
                text="Airbus Service Bulletin A320-52-1234 provides the inspection instructions.",
                lifecycle_status="operational",
            ),
            Chunk(
                chunk_id="distractor-1",
                file_instance_id="d1-file",
                ad_number="2021-0002",
                source_pdf="d1.pdf",
                page_start=2,
                page_end=2,
                section="Required Action(s) and Compliance Time(s)",
                text="cargo door inspection required at repetitive flight cycle intervals",
                lifecycle_status="operational",
            ),
            Chunk(
                chunk_id="distractor-2",
                file_instance_id="d2-file",
                ad_number="2022-0003",
                source_pdf="d2.pdf",
                page_start=2,
                page_end=2,
                section="Required Action(s) and Compliance Time(s)",
                text="forward door detailed inspection required at repetitive intervals",
                lifecycle_status="operational",
            ),
        ]
        index_dir = root / "index"
        index_dir.mkdir()
        with (index_dir / "chunks.jsonl").open("w", encoding="utf-8") as handle:
            for chunk in chunks:
                handle.write(json.dumps(asdict(chunk)) + "\n")

        connection = sqlite3.connect(index_dir / "sparse.sqlite")
        try:
            connection.execute(
                "CREATE VIRTUAL TABLE chunks USING fts5("
                "chunk_id UNINDEXED, ad_number, source_pdf UNINDEXED, "
                "page_start UNINDEXED, page_end UNINDEXED, section, text, "
                "lifecycle_status UNINDEXED)"
            )
            connection.executemany(
                "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        chunk.chunk_id,
                        chunk.ad_number,
                        chunk.source_pdf,
                        chunk.page_start,
                        chunk.page_end,
                        chunk.section,
                        chunk.text,
                        chunk.lifecycle_status,
                    )
                    for chunk in chunks
                ],
            )
            connection.commit()
        finally:
            connection.close()
        return index_dir

    def test_signal_terms_preserve_late_numeric_thresholds(self):
        filler = " ".join(f"term{letter}" for letter in "abcdefghijklmnopqrstuv")
        query = f"Which directive {filler} requires 400 flight cycles and 800 flight cycles?"
        terms = EvidenceAssemblyRetriever._signal_terms(query)
        self.assertIn("400", terms)
        self.assertIn("800", terms)

    def test_known_document_preserves_e5a_candidate_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            index_dir = self._make_index(Path(temporary))
            e5a = EngineeringAwareRetriever(index_dir)
            e5b = EvidenceAssemblyRetriever(index_dir)
            question = "Under AD 2020-0001, what cargo door inspection is required?"
            a = e5a.retrieve_lexical(question, per_route_limit=20)
            b = e5b.retrieve(question, final_candidate_limit=20)
            self.assertEqual(b["e5b_mode"], "e5a_preserved_known_document")
            self.assertEqual(
                [item["chunk_id"] for item in a["candidates"]],
                [item["chunk_id"] for item in b["candidates"]],
            )

    def test_discovery_two_stage_selects_target_and_retrieves_within_document(self):
        with tempfile.TemporaryDirectory() as temporary:
            index_dir = self._make_index(Path(temporary))
            retriever = EvidenceAssemblyRetriever(index_dir)
            question = (
                "Which cargo-door directive requires aft-door inspections at intervals "
                "not exceeding 400 flight cycles and forward-door inspections at "
                "intervals not exceeding 800 flight cycles?"
            )
            result = retriever.retrieve(
                question,
                discovery_pool_limit=20,
                document_limit=3,
                within_document_limit=4,
                final_candidate_limit=10,
            )
            self.assertEqual(result["e5b_mode"], "two_stage_discovery")
            self.assertTrue(result["document_candidates"])
            self.assertEqual(result["document_candidates"][0]["ad_number"], "2020-0001")
            self.assertEqual(result["candidates"][0]["ad_number"], "2020-0001")
            self.assertEqual(result["candidates"][0]["page_start"], 2)
            self.assertEqual(result["candidates"][0]["assembly_role"], "primary")


if __name__ == "__main__":
    unittest.main()
