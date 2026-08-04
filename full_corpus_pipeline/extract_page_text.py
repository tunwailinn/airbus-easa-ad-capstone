#!/usr/bin/env python3
"""Generate page-preserving native PDF text for the strict Airbus-only RAG corpus.

This stage is intentionally separate from content extraction. It reads the original
PDFs, validates source hashes/page counts against the frozen corpus manifest, applies
the frozen scope and unseen-document exclusions, and writes one JSONL record per PDF
page for later E0/E4 retrieval indexing.

OCR is never performed silently. Weak native-text pages are reported and make the
run non-indexable unless the caller explicitly uses --allow-needs-ocr for diagnosis.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from full_corpus_pipeline.document_io import file_sha256, read_pdf_pages


ROOT = Path(__file__).resolve().parents[1]
PAGE_TEXT_VERSION = "page-text-v1.0"
DEFAULT_MANIFEST = ROOT / "step3_pilot/source_metadata/corpus_manifest.parquet"
DEFAULT_SCOPE_AUDIT = (
    ROOT
    / "data_processed/runs/local-content-development-1804-v2.1.6/corpus_scope_audit.json"
)
DEFAULT_UNSEEN = ROOT / "evaluation_sets/unseen_incoming_5_v1/selection.csv"
DEFAULT_OUTPUT = ROOT / "data_processed/page_text_v1/operational_airbus"


def _text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"unsupported manifest format: {path}")


def select_operational_rows(
    manifest: pd.DataFrame,
    *,
    scope_audit: dict[str, Any],
    unseen_selection: pd.DataFrame | None,
    expected_count: int | None = None,
) -> pd.DataFrame:
    """Return the frozen development corpus restricted to strict Airbus-only scope."""
    frame = manifest.copy()
    if "file_instance_id" not in frame.columns:
        raise ValueError("manifest is missing file_instance_id")
    frame["file_instance_id"] = frame["file_instance_id"].astype(str)

    excluded_ids = {
        str(item["file_instance_id"])
        for key in ("excluded_records", "unknown_records")
        for item in scope_audit.get(key, [])
        if item.get("file_instance_id")
    }
    held_out_ids: set[str] = set()
    if unseen_selection is not None and not unseen_selection.empty:
        if "file_instance_id" not in unseen_selection.columns:
            raise ValueError("unseen selection is missing file_instance_id")
        held_out_ids = set(unseen_selection["file_instance_id"].astype(str))

    selected = frame[
        ~frame["file_instance_id"].isin(excluded_ids | held_out_ids)
    ].copy()

    if scope_audit.get("unknown_count", 0):
        raise ValueError(
            "scope audit still contains unknown records; resolve scope before page-text generation"
        )

    missing_scope_ids = excluded_ids - set(frame["file_instance_id"])
    if missing_scope_ids:
        raise ValueError(
            f"scope audit references IDs not present in manifest: {sorted(missing_scope_ids)[:5]}"
        )
    missing_held_out = held_out_ids - set(frame["file_instance_id"])
    if missing_held_out:
        raise ValueError(
            f"unseen selection references IDs not present in manifest: {sorted(missing_held_out)[:5]}"
        )

    if expected_count is not None and len(selected) != expected_count:
        raise ValueError(
            f"expected {expected_count} scope-eligible development PDFs, selected {len(selected)}"
        )
    return selected.sort_values(["ad_number", "file_instance_id"], kind="stable")


def build_pdf_index(pdf_root: Path) -> dict[str, list[Path]]:
    files = sorted(path for path in pdf_root.rglob("*.pdf") if path.is_file())
    if not files:
        raise ValueError(f"no PDFs found under {pdf_root}")
    by_name: dict[str, list[Path]] = {}
    for path in files:
        by_name.setdefault(path.name, []).append(path)
    return by_name


def resolve_pdf(
    row: dict[str, Any], *, pdf_root: Path, by_name: dict[str, list[Path]]
) -> Path:
    relative = Path(_text(row.get("relative_path")))
    if str(relative) and str(relative) != ".":
        direct = pdf_root / relative
        if direct.is_file():
            return direct

    name = relative.name or _text(row.get("file_name"))
    candidates = list(by_name.get(name, []))
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        file_id = _text(row.get("file_instance_id"))
        file_id_matches = [
            path
            for paths in by_name.values()
            for path in paths
            if file_id and file_id in path.stem
        ]
        if len(file_id_matches) == 1:
            return file_id_matches[0]
        raise FileNotFoundError(
            f"source PDF not found for {file_id or name}: relative_path={relative}"
        )

    expected_hash = _text(row.get("file_sha256"))
    if expected_hash:
        matches = [path for path in candidates if file_sha256(path) == expected_hash]
        if len(matches) == 1:
            return matches[0]
    raise ValueError(
        f"ambiguous source PDF for {_text(row.get('file_instance_id'))}: "
        f"{', '.join(str(path) for path in candidates[:5])}"
    )


def page_text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _page_filename(ad_number: str, file_instance_id: str) -> str:
    safe_ad = ad_number.replace("/", "_").replace(" ", "_")
    return f"{safe_ad}__{file_instance_id}.pages.jsonl"


def write_page_jsonl(
    path: Path,
    *,
    pages: list[dict[str, Any]],
    row: dict[str, Any],
    source_pdf_sha256: str,
) -> None:
    file_id = _text(row["file_instance_id"])
    ad_number = _text(row["ad_number"])
    source_pdf = _text(row.get("relative_path")) or _text(row.get("file_name"))
    with path.open("w", encoding="utf-8") as handle:
        for page in pages:
            text = str(page.get("text", ""))
            value = {
                "schema_version": PAGE_TEXT_VERSION,
                "file_instance_id": file_id,
                "ad_number": ad_number,
                "source_pdf": source_pdf,
                "source_pdf_sha256": source_pdf_sha256,
                "page": int(page["page"]),
                "page_text_sha256": page_text_sha256(text),
                "character_count": len(text),
                "non_whitespace_character_count": len("".join(text.split())),
                "needs_ocr": bool(page.get("needs_ocr", False)),
                "text": text,
            }
            handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def generate_page_text(
    *,
    pdf_root: Path,
    manifest_path: Path,
    scope_audit_path: Path,
    unseen_selection_path: Path | None,
    output_dir: Path,
    expected_count: int | None,
    minimum_native_chars: int,
    allow_needs_ocr: bool,
) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"refusing to overwrite non-empty output directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    pages_dir = output_dir / "pages"
    pages_dir.mkdir()

    manifest = _read_table(manifest_path)
    scope_audit = json.loads(scope_audit_path.read_text(encoding="utf-8"))
    unseen = (
        _read_table(unseen_selection_path)
        if unseen_selection_path is not None and unseen_selection_path.exists()
        else None
    )
    selected = select_operational_rows(
        manifest,
        scope_audit=scope_audit,
        unseen_selection=unseen,
        expected_count=expected_count,
    )
    by_name = build_pdf_index(pdf_root)

    document_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    total_pages = 0
    needs_ocr_pages = 0
    needs_ocr_documents = 0

    for row in selected.to_dict(orient="records"):
        file_id = _text(row["file_instance_id"])
        ad_number = _text(row.get("ad_number"))
        try:
            pdf_path = resolve_pdf(row, pdf_root=pdf_root, by_name=by_name)
            actual_hash = file_sha256(pdf_path)
            expected_hash = _text(row.get("file_sha256"))
            if expected_hash and actual_hash != expected_hash:
                raise ValueError(
                    f"source PDF SHA-256 mismatch: expected {expected_hash}, got {actual_hash}"
                )

            pages = read_pdf_pages(
                pdf_path, minimum_native_chars=minimum_native_chars
            )
            expected_pages = _text(row.get("page_count"))
            if expected_pages and int(float(expected_pages)) != len(pages):
                raise ValueError(
                    f"page-count mismatch: expected {int(float(expected_pages))}, got {len(pages)}"
                )

            weak_pages = [int(page["page"]) for page in pages if page.get("needs_ocr")]
            if weak_pages:
                needs_ocr_documents += 1
                needs_ocr_pages += len(weak_pages)

            output_path = pages_dir / _page_filename(ad_number, file_id)
            write_page_jsonl(
                output_path,
                pages=pages,
                row=row,
                source_pdf_sha256=actual_hash,
            )
            total_pages += len(pages)
            document_rows.append(
                {
                    "file_instance_id": file_id,
                    "ad_number": ad_number,
                    "relative_path": _text(row.get("relative_path")),
                    "source_pdf_sha256": actual_hash,
                    "page_count": len(pages),
                    "needs_ocr_page_count": len(weak_pages),
                    "needs_ocr_pages": "|".join(map(str, weak_pages)),
                    "page_text_file": str(output_path.relative_to(output_dir)),
                    "status": "needs_ocr" if weak_pages else "ok",
                }
            )
        except Exception as exc:
            failures.append(
                {
                    "file_instance_id": file_id,
                    "ad_number": ad_number,
                    "relative_path": _text(row.get("relative_path")),
                    "error": str(exc),
                }
            )

    pd.DataFrame(document_rows).to_csv(output_dir / "page_manifest.csv", index=False)
    with (output_dir / "failures.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("file_instance_id", "ad_number", "relative_path", "error"),
        )
        writer.writeheader()
        writer.writerows(failures)

    ready = (
        len(document_rows) == len(selected)
        and not failures
        and (allow_needs_ocr or needs_ocr_documents == 0)
    )
    audit = {
        "page_text_version": PAGE_TEXT_VERSION,
        "corpus_view": "strict_airbus_only_development",
        "manifest": str(manifest_path),
        "scope_audit": str(scope_audit_path),
        "unseen_selection": str(unseen_selection_path) if unseen_selection_path else None,
        "selected_document_count": len(selected),
        "successful_document_count": len(document_rows),
        "failure_count": len(failures),
        "total_page_count": total_pages,
        "needs_ocr_document_count": needs_ocr_documents,
        "needs_ocr_page_count": needs_ocr_pages,
        "minimum_native_chars": minimum_native_chars,
        "allow_needs_ocr": allow_needs_ocr,
        "ready_for_indexing": ready,
        "selection": {
            "physical_manifest_count": len(manifest),
            "scope_excluded_count": int(scope_audit.get("excluded_count", 0)),
            "scope_unknown_count": int(scope_audit.get("unknown_count", 0)),
            "held_out_unseen_count": 0 if unseen is None else len(unseen),
            "expected_selected_count": expected_count,
        },
    }
    (output_dir / "page_extraction_audit.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pdf-root",
        type=Path,
        required=True,
        help="Root directory containing the original frozen EASA PDF snapshot.",
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--scope-audit", type=Path, default=DEFAULT_SCOPE_AUDIT)
    parser.add_argument("--exclude-selection", type=Path, default=DEFAULT_UNSEEN)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--expected-count", type=int, default=1786)
    parser.add_argument("--minimum-native-chars", type=int, default=80)
    parser.add_argument(
        "--allow-needs-ocr",
        action="store_true",
        help="Diagnostic only: allow ready_for_indexing despite weak native-text pages.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = generate_page_text(
        pdf_root=args.pdf_root,
        manifest_path=args.manifest,
        scope_audit_path=args.scope_audit,
        unseen_selection_path=args.exclude_selection,
        output_dir=args.output_dir,
        expected_count=args.expected_count,
        minimum_native_chars=args.minimum_native_chars,
        allow_needs_ocr=args.allow_needs_ocr,
    )
    print(json.dumps(audit, indent=2))
    return 0 if audit["ready_for_indexing"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
