#!/usr/bin/env python3
"""Apply reviewed visual-transcription overrides to weak page-text records.

The native page extraction remains authoritative and is preserved in ``native_text``
for every overridden page. Overrides are narrow, versioned, source-hash-bound, and
may only replace pages already marked ``needs_ocr=true``. After application, the
corpus audit is recomputed and indexing remains blocked if any unresolved weak page
or extraction failure remains.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
VERIFIED_PAGE_TEXT_VERSION = "page-text-v1.1"
DEFAULT_PAGE_TEXT_DIR = ROOT / "data_processed/page_text_v1/operational_airbus"
DEFAULT_OVERRIDES = Path(__file__).with_name("page_text_visual_overrides.json")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if "page" not in value or "text" not in value:
                raise ValueError(f"{path}:{line_number}: expected page and text")
            rows.append(value)
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _nonempty_failure_count(path: Path) -> int:
    if not path.exists():
        raise FileNotFoundError(f"missing failures file: {path}")
    return len(pd.read_csv(path))


def _load_override_file(path: Path) -> tuple[str, list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    version = str(payload.get("override_version", "")).strip()
    overrides = payload.get("overrides")
    if not version or not isinstance(overrides, list):
        raise ValueError("override file must contain override_version and overrides[]")
    seen: set[tuple[str, int]] = set()
    for item in overrides:
        key = (str(item.get("file_instance_id", "")), int(item.get("page", 0)))
        if not key[0] or key[1] < 1:
            raise ValueError(f"invalid override target: {item}")
        if key in seen:
            raise ValueError(f"duplicate override target: {key}")
        seen.add(key)
    return version, overrides


def _backup_once(path: Path) -> Path:
    backup = path.with_name(path.name + ".native-v1.0.bak")
    if not backup.exists():
        shutil.copy2(path, backup)
    return backup


def apply_visual_overrides(
    page_text_dir: Path,
    *,
    overrides_path: Path = DEFAULT_OVERRIDES,
) -> dict[str, Any]:
    page_text_dir = Path(page_text_dir)
    audit_path = page_text_dir / "page_extraction_audit.json"
    manifest_path = page_text_dir / "page_manifest.csv"
    failures_path = page_text_dir / "failures.csv"
    if not audit_path.exists() or not manifest_path.exists():
        raise FileNotFoundError("page-text directory is missing audit or page manifest")

    failure_count = _nonempty_failure_count(failures_path)
    if failure_count:
        raise ValueError(f"refusing overrides while {failure_count} extraction failures remain")

    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    page_manifest = pd.read_csv(
        manifest_path, dtype={"file_instance_id": str, "ad_number": str}
    )
    override_version, overrides = _load_override_file(overrides_path)

    _backup_once(audit_path)
    _backup_once(manifest_path)

    applied: list[dict[str, Any]] = []
    for override in overrides:
        file_id = str(override["file_instance_id"])
        ad_number = str(override["ad_number"])
        page_number = int(override["page"])
        mask = (
            page_manifest["file_instance_id"].astype(str).eq(file_id)
            & page_manifest["ad_number"].astype(str).eq(ad_number)
        )
        matches = page_manifest[mask]
        if len(matches) != 1:
            raise ValueError(
                f"expected one page-manifest row for {ad_number}/{file_id}, found {len(matches)}"
            )
        idx = matches.index[0]
        manifest_row = matches.iloc[0]
        expected_pdf_hash = str(override["source_pdf_sha256"])
        if str(manifest_row["source_pdf_sha256"]) != expected_pdf_hash:
            raise ValueError(f"source hash mismatch for override {override['override_id']}")

        page_file = page_text_dir / str(manifest_row["page_text_file"])
        if not page_file.exists():
            raise FileNotFoundError(page_file)
        _backup_once(page_file)
        rows = _load_jsonl(page_file)
        targets = [row for row in rows if int(row["page"]) == page_number]
        if len(targets) != 1:
            raise ValueError(
                f"expected one page {page_number} in {page_file}, found {len(targets)}"
            )
        target = targets[0]
        if str(target.get("source_pdf_sha256", "")) != expected_pdf_hash:
            raise ValueError(f"page source hash mismatch for override {override['override_id']}")

        already = target.get("visual_override_id") == override["override_id"]
        if not already and not bool(target.get("needs_ocr", False)):
            raise ValueError(
                f"override target {override['override_id']} is not marked needs_ocr=true"
            )
        native_text = str(target.get("native_text", target.get("text", "")))
        for fragment in override.get("native_text_expected_contains", []):
            if str(fragment).casefold() not in native_text.casefold():
                raise ValueError(
                    f"override {override['override_id']} native-text guard failed: {fragment!r}"
                )

        replacement = str(override["text"]).strip()
        if not replacement:
            raise ValueError(f"override {override['override_id']} has empty text")
        target.update(
            {
                "schema_version": VERIFIED_PAGE_TEXT_VERSION,
                "native_text": native_text,
                "native_needs_ocr": True,
                "text": replacement,
                "page_text_sha256": _sha256_text(replacement),
                "character_count": len(replacement),
                "non_whitespace_character_count": len("".join(replacement.split())),
                "needs_ocr": False,
                "text_source": "visual_transcription_override",
                "visual_override_id": str(override["override_id"]),
                "visual_override_version": override_version,
                "visual_override_method": str(
                    override.get("method", "visual_transcription")
                ),
            }
        )
        _write_jsonl(page_file, rows)

        remaining_weak = [
            int(row["page"]) for row in rows if bool(row.get("needs_ocr", False))
        ]
        page_manifest.loc[idx, "needs_ocr_page_count"] = len(remaining_weak)
        page_manifest.loc[idx, "needs_ocr_pages"] = "|".join(map(str, remaining_weak))
        page_manifest.loc[idx, "status"] = "ok" if not remaining_weak else "needs_ocr"
        page_manifest.loc[idx, "visual_override_count"] = sum(
            1
            for row in rows
            if row.get("text_source") == "visual_transcription_override"
        )
        applied.append(
            {
                "override_id": str(override["override_id"]),
                "file_instance_id": file_id,
                "ad_number": ad_number,
                "page": page_number,
                "source_pdf_sha256": expected_pdf_hash,
                "method": str(override.get("method", "visual_transcription")),
            }
        )

    page_manifest.to_csv(manifest_path, index=False)

    unresolved_docs = 0
    unresolved_pages = 0
    for row in page_manifest.to_dict(orient="records"):
        page_file = page_text_dir / str(row["page_text_file"])
        pages = _load_jsonl(page_file)
        weak = sum(bool(page.get("needs_ocr", False)) for page in pages)
        if weak:
            unresolved_docs += 1
            unresolved_pages += weak

    base_version = str(audit.get("page_text_version", "page-text-v1.0"))
    audit.update(
        {
            "page_text_version": VERIFIED_PAGE_TEXT_VERSION,
            "base_page_text_version": base_version,
            "visual_override_version": override_version,
            "visual_override_count": len(applied),
            "visual_overrides_applied": applied,
            "native_needs_ocr_document_count": int(
                audit.get("needs_ocr_document_count", 0)
            ),
            "native_needs_ocr_page_count": int(audit.get("needs_ocr_page_count", 0)),
            "needs_ocr_document_count": unresolved_docs,
            "needs_ocr_page_count": unresolved_pages,
            "ready_for_indexing": bool(
                int(audit.get("successful_document_count", 0))
                == int(audit.get("selected_document_count", -1))
                and int(audit.get("failure_count", failure_count)) == 0
                and unresolved_pages == 0
            ),
        }
    )
    audit_path.write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "page_text_dir", type=Path, nargs="?", default=DEFAULT_PAGE_TEXT_DIR
    )
    parser.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = apply_visual_overrides(args.page_text_dir, overrides_path=args.overrides)
    print(json.dumps(audit, indent=2))
    return 0 if audit["ready_for_indexing"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
