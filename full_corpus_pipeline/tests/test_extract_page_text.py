from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from full_corpus_pipeline.extract_page_text import (
    generate_page_text,
    select_operational_rows,
)


class PageTextSelectionTests(unittest.TestCase):
    def test_scope_and_unseen_are_both_excluded(self) -> None:
        manifest = pd.DataFrame(
            [
                {"file_instance_id": "a", "ad_number": "2000-0001"},
                {"file_instance_id": "b", "ad_number": "2000-0002"},
                {"file_instance_id": "c", "ad_number": "2000-0003"},
                {"file_instance_id": "d", "ad_number": "2000-0004"},
            ]
        )
        scope = {
            "unknown_count": 0,
            "excluded_records": [{"file_instance_id": "c"}],
            "unknown_records": [],
        }
        unseen = pd.DataFrame([{"file_instance_id": "d"}])
        selected = select_operational_rows(
            manifest,
            scope_audit=scope,
            unseen_selection=unseen,
            expected_count=2,
        )
        self.assertEqual(["a", "b"], selected["file_instance_id"].tolist())

    def test_unknown_scope_blocks_generation(self) -> None:
        manifest = pd.DataFrame(
            [{"file_instance_id": "a", "ad_number": "2000-0001"}]
        )
        with self.assertRaisesRegex(ValueError, "scope audit still contains unknown"):
            select_operational_rows(
                manifest,
                scope_audit={"unknown_count": 1, "unknown_records": []},
                unseen_selection=None,
                expected_count=1,
            )


class PageTextGenerationTests(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[Path, Path, Path]:
        pdf_root = root / "pdfs"
        pdf_root.mkdir()
        pdf = pdf_root / "sample.pdf"
        pdf.write_bytes(b"frozen-pdf-bytes")
        digest = hashlib.sha256(pdf.read_bytes()).hexdigest()

        manifest = root / "manifest.csv"
        pd.DataFrame(
            [
                {
                    "file_instance_id": digest[:16],
                    "ad_number": "2020-0001",
                    "relative_path": "sample.pdf",
                    "file_sha256": digest,
                    "page_count": 2,
                }
            ]
        ).to_csv(manifest, index=False)
        scope = root / "scope.json"
        scope.write_text(
            json.dumps(
                {
                    "excluded_count": 0,
                    "unknown_count": 0,
                    "excluded_records": [],
                    "unknown_records": [],
                }
            ),
            encoding="utf-8",
        )
        return pdf_root, manifest, scope

    @patch("full_corpus_pipeline.extract_page_text.read_pdf_pages")
    def test_writes_page_jsonl_and_ready_audit(self, read_pages) -> None:
        read_pages.return_value = [
            {"page": 1, "text": "First page text", "needs_ocr": False},
            {"page": 2, "text": "Second page text", "needs_ocr": False},
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf_root, manifest, scope = self._fixture(root)
            output = root / "out"
            audit = generate_page_text(
                pdf_root=pdf_root,
                manifest_path=manifest,
                scope_audit_path=scope,
                unseen_selection_path=None,
                output_dir=output,
                expected_count=1,
                minimum_native_chars=80,
                allow_needs_ocr=False,
            )
            self.assertTrue(audit["ready_for_indexing"])
            self.assertEqual(1, audit["successful_document_count"])
            self.assertEqual(2, audit["total_page_count"])
            page_files = list((output / "pages").glob("*.jsonl"))
            self.assertEqual(1, len(page_files))
            records = [json.loads(line) for line in page_files[0].read_text().splitlines()]
            self.assertEqual([1, 2], [record["page"] for record in records])
            self.assertTrue(all(record["page_text_sha256"] for record in records))

    @patch("full_corpus_pipeline.extract_page_text.read_pdf_pages")
    def test_ocr_required_page_blocks_indexing_by_default(self, read_pages) -> None:
        read_pages.return_value = [
            {"page": 1, "text": "", "needs_ocr": True},
            {"page": 2, "text": "Second page text", "needs_ocr": False},
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf_root, manifest, scope = self._fixture(root)
            audit = generate_page_text(
                pdf_root=pdf_root,
                manifest_path=manifest,
                scope_audit_path=scope,
                unseen_selection_path=None,
                output_dir=root / "out",
                expected_count=1,
                minimum_native_chars=80,
                allow_needs_ocr=False,
            )
            self.assertFalse(audit["ready_for_indexing"])
            self.assertEqual(1, audit["needs_ocr_document_count"])
            self.assertEqual(1, audit["needs_ocr_page_count"])


if __name__ == "__main__":
    unittest.main()
