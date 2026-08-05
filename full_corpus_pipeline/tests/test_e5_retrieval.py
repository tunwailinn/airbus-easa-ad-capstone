import json
import sqlite3
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from full_corpus_pipeline.e5_retrieval import EngineeringAwareRetriever
from full_corpus_pipeline.retrieval import Chunk


class E5RetrievalTests(unittest.TestCase):
    def _make_index(self, root: Path) -> Path:
        chunks = [
            Chunk(
                chunk_id="a1",
                file_instance_id="f1",
                ad_number="2020-0001",
                source_pdf="a.pdf",
                page_start=1,
                page_end=1,
                section="Applicability",
                text="Airbus A320 aircraft are affected by this directive.",
                lifecycle_status="operational",
            ),
            Chunk(
                chunk_id="a2",
                file_instance_id="f1",
                ad_number="2020-0001",
                source_pdf="a.pdf",
                page_start=2,
                page_end=2,
                section="Required Action(s) and Compliance Time(s)",
                text="Inspect the affected area within 500 flight cycles.",
                lifecycle_status="operational",
            ),
            Chunk(
                chunk_id="b1",
                file_instance_id="f2",
                ad_number="2021-0002",
                source_pdf="b.pdf",
                page_start=2,
                page_end=2,
                section="Required Action(s) and Compliance Time(s)",
                text="Inspect the affected area within 500 flight cycles.",
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

    def test_known_document_retrieval_never_returns_other_ad(self):
        with tempfile.TemporaryDirectory() as temporary:
            index_dir = self._make_index(Path(temporary))
            retriever = EngineeringAwareRetriever(index_dir)
            result = retriever.retrieve_lexical(
                "Under AD 2020-0001, when must the inspection be done?"
            )
            self.assertEqual(result["route"]["mode"], "known_document")
            self.assertTrue(result["candidates"])
            self.assertEqual(
                {item["ad_number"] for item in result["candidates"]},
                {"2020-0001"},
            )
            self.assertEqual(
                result["candidates"][0]["section"],
                "Required Action(s) and Compliance Time(s)",
            )

    def test_known_document_identifier_is_removed_from_ranking_query(self):
        with tempfile.TemporaryDirectory() as temporary:
            index_dir = self._make_index(Path(temporary))
            retriever = EngineeringAwareRetriever(index_dir)
            result = retriever.retrieve_lexical(
                "Under EASA AD 2020-0001, when must the inspection be done?"
            )
            self.assertNotIn("2020-0001", result["ranking_query"])
            self.assertNotIn("EASA AD", result["ranking_query"])
            self.assertIn("inspection", result["ranking_query"])

    def test_discovery_query_can_search_globally(self):
        with tempfile.TemporaryDirectory() as temporary:
            index_dir = self._make_index(Path(temporary))
            retriever = EngineeringAwareRetriever(index_dir)
            question = "Which AD requires inspection within 500 flight cycles?"
            result = retriever.retrieve_lexical(question)
            self.assertEqual(result["route"]["mode"], "discovery")
            self.assertEqual(result["ranking_query"], question)
            self.assertGreaterEqual(len({item["ad_number"] for item in result["candidates"]}), 2)

    def test_missing_explicit_ad_is_reported_not_replaced(self):
        with tempfile.TemporaryDirectory() as temporary:
            index_dir = self._make_index(Path(temporary))
            retriever = EngineeringAwareRetriever(index_dir)
            result = retriever.retrieve_lexical("What does AD 2022-9999 require?")
            self.assertEqual(result["candidate_count"], 0)
            self.assertEqual(len(result["route_errors"]), 1)


if __name__ == "__main__":
    unittest.main()
