"""PDF/page-text input utilities shared by extraction and retrieval."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_text(value: str) -> str:
    return re.sub(r"[ \t]+", " ", value.replace("\r", "\n")).strip()


def read_pdf_pages(path: Path, *, minimum_native_chars: int = 80) -> list[dict[str, Any]]:
    """Extract native text page by page; report when OCR is required.

    OCR is deliberately not performed silently. A caller must route weak pages
    to its configured OCR service or derivative folder.
    """
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover - dependency gate
        raise RuntimeError("PyMuPDF is required to read uploaded PDFs") from exc
    pages: list[dict[str, Any]] = []
    with fitz.open(path) as document:
        for page_number, page in enumerate(document, 1):
            text = normalize_text(page.get_text("text"))
            pages.append(
                {
                    "page": page_number,
                    "text": text,
                    "needs_ocr": len(re.sub(r"\s+", "", text)) < minimum_native_chars,
                }
            )
    if not pages:
        raise ValueError(f"PDF contains no pages: {path}")
    return pages


def read_page_jsonl(path: Path) -> list[dict[str, Any]]:
    pages = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if "page" not in value or "text" not in value:
                raise ValueError(f"{path}:{line_number}: expected page and text")
            pages.append(value)
    return pages


def joined_page_text(pages: list[dict[str, Any]]) -> str:
    return "\n\n".join(
        f"[PAGE {page['page']}]\n{page.get('text', '')}" for page in pages
    )
