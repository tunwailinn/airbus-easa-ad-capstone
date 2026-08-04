import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from full_corpus_pipeline.build_retrieval_experiments import (
    _as_bool,
    chunk_stats,
    strict_section_chunk_pages,
    validate_page_source,
)
from full_corpus_pipeline.retrieval import flat_chunk_pages


class RetrievalExperimentBuildTests(unittest.TestCase):
    def _page_root(self, root: Path, *, version: str = "page-text-v1.1") -> Path:
        page_root = root / "page_text_v1_1" / "operational_airbus"
        pages = page_root / "pages"
        pages.mkdir(parents=True)
        audit = {
            "page_text_version": version,
            "selected_document_count": 2,
            "successful_document_count": 2,
            "failure_count": 0,
            "needs_ocr_document_count": 0,
            "needs_ocr_page_count": 0,
            "ready_for_indexing": True,
        }
        (page_root / "page_extraction_audit.json").write_text(
            json.dumps(audit), encoding="utf-8"
        )
        pd.DataFrame(
            [
                {
                    "file_instance_id": "a",
                    "ad_number": "2026-0001",
                    "relative_path": "a.pdf",
                    "is_latest_version": True,
                },
                {
                    "file_instance_id": "b",
                    "ad_number": "2026-0002",
                    "relative_path": "b.pdf",
                    "is_latest_version": False,
                },
            ]
        ).to_csv(page_root / "retrieval_manifest.csv", index=False)
        for file_id, ad_number in (("a", "2026-0001"), ("b", "2026-0002")):
            (pages / f"{ad_number}__{file_id}.pages.jsonl").write_text(
                json.dumps(
                    {
                        "schema_version": version,
                        "file_instance_id": file_id,
                        "ad_number": ad_number,
                        "source_pdf": f"{file_id}.pdf",
                        "page": 1,
                        "needs_ocr": False,
                        "text": "Reason\nHydraulic inspection is required.",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
        return page_root

    def test_verified_page_source_gate_accepts_v11(self):
        with tempfile.TemporaryDirectory() as tmp:
            page_root = self._page_root(Path(tmp))
            manifest, audit = validate_page_source(page_root, expected_count=2)
            self.assertEqual(len(manifest), 2)
            self.assertEqual(audit["page_text_version"], "page-text-v1.1")
            self.assertEqual(manifest["is_latest_version"].tolist(), [True, False])

    def test_manifest_boolean_parser_does_not_treat_false_string_as_true(self):
        self.assertTrue(_as_bool("True"))
        self.assertFalse(_as_bool("False"))
        self.assertFalse(_as_bool("0"))
        self.assertTrue(_as_bool("1"))
        with self.assertRaisesRegex(ValueError, "unrecognized boolean"):
            _as_bool("maybe")

    def test_page_source_gate_rejects_old_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            page_root = self._page_root(Path(tmp), version="page-text-v1.0")
            with self.assertRaisesRegex(ValueError, "expected page-text-v1.1"):
                validate_page_source(page_root, expected_count=2)

    def test_chunk_stats_cover_flat_and_strict_section_chunks(self):
        pages = [
            {"page": 1, "text": "Reason\nHydraulic accumulator inspection required."},
            {"page": 2, "text": "Required Actions\nInspect within 500 flight cycles."},
        ]
        flat = flat_chunk_pages(
            pages,
            file_instance_id="a",
            ad_number="2026-0001",
            source_pdf="a.pdf",
            chunk_tokens=350,
        )
        section = strict_section_chunk_pages(
            pages,
            file_instance_id="a",
            ad_number="2026-0001",
            source_pdf="a.pdf",
            minimum_tokens=1,
            maximum_tokens=450,
        )
        flat_stats = chunk_stats(flat)
        section_stats = chunk_stats(section)
        self.assertEqual(flat_stats["document_count"], 1)
        self.assertEqual(section_stats["document_count"], 1)
        self.assertEqual(flat_stats["token_count_method"], "whitespace_split")
        self.assertEqual(section_stats["token_count_method"], "whitespace_split")
        self.assertLessEqual(flat_stats["max_tokens"], 350)
        self.assertLessEqual(section_stats["max_tokens"], 450)

    def test_chunk_stats_match_construction_units_for_punctuation_heavy_text(self):
        text = " ".join(["A+B"] * 350)
        chunks = flat_chunk_pages(
            [{"page": 1, "text": text}],
            file_instance_id="a",
            ad_number="2026-0001",
            source_pdf="a.pdf",
            chunk_tokens=350,
        )
        stats = chunk_stats(chunks)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(stats["max_tokens"], 350)

    def test_strict_section_chunker_enforces_whitespace_limit(self):
        # Reproduces the v1.1 failure mode: punctuation-only whitespace units
        # are invisible to TOKEN_RE but still count toward the declared chunk
        # size policy. The strict v1.2 E4 chunker must split them.
        body = " ".join(["inspection"] * 430 + ["—"] * 46)
        chunks = strict_section_chunk_pages(
            [{"page": 1, "text": "Reason\n" + body}],
            file_instance_id="a",
            ad_number="2026-0001",
            source_pdf="a.pdf",
            minimum_tokens=250,
            maximum_tokens=450,
        )
        stats = chunk_stats(chunks)
        self.assertGreaterEqual(len(chunks), 2)
        self.assertLessEqual(stats["max_tokens"], 450)
        self.assertEqual(sum(len(chunk.text.split()) for chunk in chunks), 476)


if __name__ == "__main__":
    unittest.main()
