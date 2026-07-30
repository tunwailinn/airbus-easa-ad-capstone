#!/usr/bin/env python3
"""Retrieve and verify the 30 frozen Step 3 source PDFs.

The utility reads ``selection/pilot_selection.csv``, downloads only official
EASA ``pdf_url`` values, and writes exclusively under ``step3_pilot`` by
default.  A PDF is promoted from its resumable ``.part`` file only after its
SHA-256 matches the frozen selection.  Verified PDFs are then converted to
page-delimited JSONL with one JSON object per PDF page.

Nothing in ``corpus_raw`` is opened for writing or used as a download target.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
DEFAULT_SELECTION = ROOT / "selection" / "pilot_selection.csv"
DEFAULT_PDF_DIR = ROOT / "source_pdfs"
DEFAULT_PAGE_TEXT_DIR = ROOT / "page_text"
DEFAULT_REPORT_JSON = ROOT / "source_verification_report.json"
DEFAULT_REPORT_CSV = ROOT / "source_verification_report.csv"

EXPECTED_DOCUMENT_COUNT = 30
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
SAFE_FILE_INSTANCE_RE = re.compile(r"^[0-9a-fA-F]{16}$")
SAFE_AD_NUMBER_RE = re.compile(r"^(?:19|20)[0-9]{2}-[0-9]{4}(?:R[1-9][0-9]*)?(?:-E)?$")
REQUIRED_SELECTION_COLUMNS = {
    "ad_number",
    "base_ad_number",
    "logical_version_key",
    "file_name",
    "relative_path",
    "file_instance_id",
    "content_id",
    "file_sha256",
    "normalized_text_sha256",
    "page_count",
    "pdf_url",
}


class RetrievalError(RuntimeError):
    """Base error for selection, retrieval, and extraction failures."""


class IntegrityError(RetrievalError):
    """Raised when a frozen hash, page count, or derived cache disagrees."""


@dataclass(frozen=True)
class SelectionRow:
    ad_number: str
    base_ad_number: str
    logical_version_key: str
    file_name: str
    relative_path: str
    file_instance_id: str
    content_id: str
    file_sha256: str
    normalized_text_sha256: str | None
    page_count: int
    pdf_url: str

    @property
    def page_jsonl_name(self) -> str:
        return f"{self.ad_number}__{self.file_instance_id}.pages.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_path(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def atomic_write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def is_official_easa_url(value: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(value)
        hostname = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError:
        return False
    official_host = hostname == "easa.europa.eu" or hostname.endswith(
        ".easa.europa.eu"
    )
    return (
        parsed.scheme.lower() == "https"
        and official_host
        and parsed.username is None
        and parsed.password is None
        and port in {None, 443}
    )


class OfficialEasaRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects that leave an official EASA HTTPS hostname."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        destination = urllib.parse.urljoin(req.full_url, newurl)
        if not is_official_easa_url(destination):
            raise RetrievalError(
                f"Refusing non-EASA redirect for {req.full_url!r}: {destination!r}"
            )
        return super().redirect_request(req, fp, code, msg, headers, destination)


def ensure_safe_output_path(path: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if any(part.lower() == "corpus_raw" for part in resolved.parts):
        raise RetrievalError(f"{label} must not be inside corpus_raw: {resolved}")
    return resolved


def selection_file_sha256(path: Path) -> str:
    if not path.is_file():
        raise RetrievalError(f"Selection CSV not found: {path}")
    return sha256_path(path)


def read_selection(path: Path) -> list[SelectionRow]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_SELECTION_COLUMNS - columns)
        if missing:
            raise RetrievalError(
                "Selection CSV is missing required columns: " + ", ".join(missing)
            )
        raw_rows = list(reader)

    if len(raw_rows) != EXPECTED_DOCUMENT_COUNT:
        raise RetrievalError(
            f"Expected exactly {EXPECTED_DOCUMENT_COUNT} selected rows, "
            f"found {len(raw_rows)}"
        )

    rows: list[SelectionRow] = []
    for line_number, raw in enumerate(raw_rows, start=2):
        ad_number = raw["ad_number"].strip()
        file_name = raw["file_name"].strip()
        file_instance_id = raw["file_instance_id"].strip().lower()
        expected_sha = raw["file_sha256"].strip().lower()
        pdf_url = raw["pdf_url"].strip()

        if not SAFE_AD_NUMBER_RE.fullmatch(ad_number):
            raise RetrievalError(
                f"Line {line_number}: invalid EASA AD number {ad_number!r}"
            )
        if not file_name or Path(file_name).name != file_name or not file_name.lower().endswith(".pdf"):
            raise RetrievalError(
                f"Line {line_number}: unsafe or non-PDF file_name {file_name!r}"
            )
        if not SAFE_FILE_INSTANCE_RE.fullmatch(file_instance_id):
            raise RetrievalError(
                f"Line {line_number}: invalid file_instance_id {file_instance_id!r}"
            )
        if not SHA256_RE.fullmatch(expected_sha):
            raise RetrievalError(
                f"Line {line_number}: invalid file_sha256 {expected_sha!r}"
            )
        normalized_hash = raw["normalized_text_sha256"].strip().lower() or None
        if normalized_hash is not None and not SHA256_RE.fullmatch(normalized_hash):
            raise RetrievalError(
                f"Line {line_number}: invalid normalized_text_sha256 "
                f"{normalized_hash!r}"
            )
        if not is_official_easa_url(pdf_url):
            raise RetrievalError(
                f"Line {line_number}: pdf_url is not official EASA HTTPS: {pdf_url!r}"
            )
        try:
            page_count = int(raw["page_count"])
        except ValueError as exc:
            raise RetrievalError(
                f"Line {line_number}: invalid page_count {raw['page_count']!r}"
            ) from exc
        if page_count < 1:
            raise RetrievalError(
                f"Line {line_number}: page_count must be positive, got {page_count}"
            )

        rows.append(
            SelectionRow(
                ad_number=ad_number,
                base_ad_number=raw["base_ad_number"].strip(),
                logical_version_key=raw["logical_version_key"].strip(),
                file_name=file_name,
                relative_path=raw["relative_path"].strip(),
                file_instance_id=file_instance_id,
                content_id=raw["content_id"].strip().lower(),
                file_sha256=expected_sha,
                normalized_text_sha256=normalized_hash,
                page_count=page_count,
                pdf_url=pdf_url,
            )
        )

    unique_fields = {
        "ad_number": [row.ad_number for row in rows],
        "logical_version_key": [row.logical_version_key for row in rows],
        "file_name": [row.file_name for row in rows],
        "file_instance_id": [row.file_instance_id for row in rows],
        "file_sha256": [row.file_sha256 for row in rows],
        "pdf_url": [row.pdf_url for row in rows],
    }
    for label, values in unique_fields.items():
        duplicates = sorted({value for value in values if values.count(value) > 1})
        if duplicates:
            raise RetrievalError(
                f"Selection CSV has duplicate {label} value(s): {duplicates}"
            )
    return rows


def initial_document_report(row: SelectionRow, pdf_dir: Path, page_dir: Path) -> dict[str, Any]:
    return {
        "ad_number": row.ad_number,
        "file_instance_id": row.file_instance_id,
        "file_name": row.file_name,
        "pdf_url": row.pdf_url,
        "expected_sha256": row.file_sha256,
        "actual_sha256": None,
        "expected_page_count": row.page_count,
        "actual_page_count": None,
        "pdf_bytes": None,
        "pdf_status": "pending",
        "page_text_status": "pending",
        "page_text_file": str(page_dir / row.page_jsonl_name),
        "page_text_sha256": None,
        "extracted_char_count": None,
        "error": None,
        "local_pdf": str(pdf_dir / row.file_name),
    }


class VerificationReport:
    def __init__(
        self,
        *,
        selection: Path,
        selection_sha256: str | None,
        pdf_dir: Path,
        page_dir: Path,
        report_json: Path,
        report_csv: Path,
    ) -> None:
        self.selection = selection
        self.selection_sha256 = selection_sha256
        self.pdf_dir = pdf_dir
        self.page_dir = page_dir
        self.report_json = report_json
        self.report_csv = report_csv
        self.started_at = utc_now()
        self.completed_at: str | None = None
        self.status = "initializing"
        self.fatal_error: str | None = None
        self.aggregate_page_text_file: str | None = None
        self.aggregate_page_text_sha256: str | None = None
        self.documents: list[dict[str, Any]] = []

    def summary(self) -> dict[str, int]:
        return {
            "expected_documents": EXPECTED_DOCUMENT_COUNT,
            "reported_documents": len(self.documents),
            "verified_pdfs": sum(
                item["pdf_status"] in {"downloaded_verified", "resumed_verified", "reused_verified"}
                for item in self.documents
            ),
            "verified_page_text_files": sum(
                item["page_text_status"] in {"extracted_verified", "reused_verified"}
                for item in self.documents
            ),
            "failed_documents": sum(bool(item.get("error")) for item in self.documents),
            "expected_pages": sum(
                int(item["expected_page_count"]) for item in self.documents
            ),
            "verified_pages": sum(
                int(item["actual_page_count"] or 0) for item in self.documents
                if item["page_text_status"] in {"extracted_verified", "reused_verified"}
            ),
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "report_version": "1.0.0",
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "selection_csv": str(self.selection),
            "selection_csv_sha256": self.selection_sha256,
            "pdf_output_dir": str(self.pdf_dir),
            "page_text_output_dir": str(self.page_dir),
            "aggregate_page_text_file": self.aggregate_page_text_file,
            "aggregate_page_text_sha256": self.aggregate_page_text_sha256,
            "summary": self.summary(),
            "fatal_error": self.fatal_error,
            "documents": self.documents,
        }

    def write(self) -> None:
        atomic_write_text(
            self.report_json,
            json.dumps(self.as_dict(), indent=2, ensure_ascii=False) + "\n",
        )
        fieldnames = [
            "ad_number",
            "file_instance_id",
            "file_name",
            "pdf_url",
            "expected_sha256",
            "actual_sha256",
            "expected_page_count",
            "actual_page_count",
            "pdf_bytes",
            "pdf_status",
            "page_text_status",
            "page_text_file",
            "page_text_sha256",
            "extracted_char_count",
            "error",
            "local_pdf",
        ]
        temporary = self.report_csv.with_name(self.report_csv.name + ".tmp")
        temporary.parent.mkdir(parents=True, exist_ok=True)
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.documents)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.report_csv)


def has_pdf_header(path: Path) -> bool:
    with path.open("rb") as handle:
        return b"%PDF-" in handle.read(1024)


def unique_quarantine_path(path: Path, reason: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = path.with_name(f"{path.name}.{reason}.{timestamp}")
    counter = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.name}.{reason}.{timestamp}.{counter}")
        counter += 1
    return candidate


def verify_existing_pdfs(
    rows: Iterable[SelectionRow],
    pdf_dir: Path,
    document_reports: dict[str, dict[str, Any]],
) -> list[str]:
    mismatches: list[str] = []
    for row in rows:
        target = pdf_dir / row.file_name
        if not target.exists():
            continue
        if not target.is_file():
            mismatches.append(f"{row.ad_number}: expected a file at {target}")
            continue
        actual = sha256_path(target)
        report = document_reports[row.file_instance_id]
        report["actual_sha256"] = actual
        report["pdf_bytes"] = target.stat().st_size
        if actual != row.file_sha256:
            report["pdf_status"] = "hash_mismatch"
            report["error"] = (
                f"existing PDF SHA-256 mismatch: expected {row.file_sha256}, got {actual}"
            )
            mismatches.append(f"{row.ad_number}: {report['error']}")
        elif not has_pdf_header(target):
            report["pdf_status"] = "invalid_pdf_header"
            report["error"] = "verified bytes do not contain a PDF header in the first 1024 bytes"
            mismatches.append(f"{row.ad_number}: {report['error']}")
        else:
            report["pdf_status"] = "reused_verified"
    return mismatches


def stream_response(response, target: Path, mode: str, chunk_size: int) -> None:  # noqa: ANN001
    with target.open(mode) as handle:
        shutil.copyfileobj(response, handle, length=chunk_size)
        handle.flush()
        os.fsync(handle.fileno())


def download_pdf(
    row: SelectionRow,
    target: Path,
    *,
    opener: urllib.request.OpenerDirector,
    timeout: float,
    retries: int,
    chunk_size: int,
    user_agent: str,
) -> str:
    partial = target.with_name(target.name + ".part")
    target.parent.mkdir(parents=True, exist_ok=True)

    if partial.exists() and partial.is_file():
        partial_hash = sha256_path(partial)
        if partial_hash == row.file_sha256 and has_pdf_header(partial):
            os.replace(partial, target)
            return "resumed_verified"

    last_error: Exception | None = None
    reset_range_once = False
    resumed_transfer = False
    for attempt in range(1, retries + 1):
        offset = partial.stat().st_size if partial.exists() else 0
        headers = {
            "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.1",
            "User-Agent": user_agent,
        }
        if offset:
            headers["Range"] = f"bytes={offset}-"
        request = urllib.request.Request(row.pdf_url, headers=headers)
        try:
            with opener.open(request, timeout=timeout) as response:
                final_url = response.geturl()
                if not is_official_easa_url(final_url):
                    raise RetrievalError(
                        f"Final response URL is not official EASA HTTPS: {final_url!r}"
                    )
                status = getattr(response, "status", response.getcode())
                mode = "ab" if offset and status == 206 else "wb"
                resumed_transfer = mode == "ab"
                stream_response(response, partial, mode, chunk_size)
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 416 and offset and not reset_range_once:
                quarantine = unique_quarantine_path(partial, "range-not-satisfiable")
                os.replace(partial, quarantine)
                reset_range_once = True
                last_error = exc
                continue
            last_error = exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc

        if attempt < retries:
            time.sleep(min(2 ** (attempt - 1), 8))
    else:
        raise RetrievalError(
            f"Download failed after {retries} attempt(s) for {row.ad_number}: {last_error}"
        ) from last_error

    actual = sha256_path(partial)
    if actual != row.file_sha256:
        quarantine = unique_quarantine_path(partial, "sha256-mismatch")
        os.replace(partial, quarantine)
        raise IntegrityError(
            f"Downloaded SHA-256 mismatch for {row.ad_number}: expected "
            f"{row.file_sha256}, got {actual}; bytes retained at {quarantine}"
        )
    if not has_pdf_header(partial):
        quarantine = unique_quarantine_path(partial, "invalid-pdf-header")
        os.replace(partial, quarantine)
        raise IntegrityError(
            f"Downloaded bytes for {row.ad_number} have no PDF header; "
            f"bytes retained at {quarantine}"
        )
    os.replace(partial, target)
    return "resumed_verified" if resumed_transfer else "downloaded_verified"


def parse_page_jsonl(path: Path, row: SelectionRow) -> tuple[int, int]:
    page_numbers: list[int] = []
    character_count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                raise IntegrityError(f"{path}: blank JSONL line {line_number}")
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise IntegrityError(
                    f"{path}: invalid JSON on line {line_number}: {exc}"
                ) from exc
            if item.get("ad_number") != row.ad_number:
                raise IntegrityError(f"{path}: AD mismatch on line {line_number}")
            if item.get("file_instance_id") != row.file_instance_id:
                raise IntegrityError(
                    f"{path}: file_instance_id mismatch on line {line_number}"
                )
            if item.get("pdf_sha256") != row.file_sha256:
                raise IntegrityError(f"{path}: PDF hash mismatch on line {line_number}")
            text = item.get("text")
            if not isinstance(text, str):
                raise IntegrityError(f"{path}: text is not a string on line {line_number}")
            if item.get("page_text_sha256") != sha256_text(text):
                raise IntegrityError(
                    f"{path}: page-text hash mismatch on line {line_number}"
                )
            page_number = item.get("page_number")
            if not isinstance(page_number, int):
                raise IntegrityError(
                    f"{path}: page_number is not an integer on line {line_number}"
                )
            page_numbers.append(page_number)
            character_count += len(text)

    expected_numbers = list(range(1, row.page_count + 1))
    if page_numbers != expected_numbers:
        raise IntegrityError(
            f"{path}: expected page sequence {expected_numbers}, got {page_numbers}"
        )
    return len(page_numbers), character_count


def pypdf_version() -> str:
    try:
        import pypdf  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RetrievalError(
            "Page extraction requires pypdf. Install it with: "
            "python3 -m pip install 'pypdf>=4,<7'"
        ) from exc
    return str(getattr(pypdf, "__version__", "unknown"))


def extract_page_jsonl(row: SelectionRow, pdf_path: Path, output_path: Path) -> tuple[int, int]:
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RetrievalError(
            "Page extraction requires pypdf. Install it with: "
            "python3 -m pip install 'pypdf>=4,<7'"
        ) from exc

    library_version = pypdf_version()
    reader = PdfReader(str(pdf_path), strict=False)
    if reader.is_encrypted and reader.decrypt("") == 0:
        raise RetrievalError(f"Cannot decrypt selected PDF with an empty password: {pdf_path}")
    actual_page_count = len(reader.pages)
    if actual_page_count != row.page_count:
        raise IntegrityError(
            f"Page-count mismatch for {row.ad_number}: selection expects "
            f"{row.page_count}, pypdf found {actual_page_count}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(output_path.name + ".tmp")
    character_count = 0
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for page_index, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text(extraction_mode="layout") or ""
                extraction_mode = "layout"
            except TypeError:
                text = page.extract_text() or ""
                extraction_mode = "plain"
            character_count += len(text)
            item = {
                "page_record_schema_version": "1.0.0",
                "page_id": f"{row.file_instance_id}:p{page_index:04d}",
                "ad_number": row.ad_number,
                "base_ad_number": row.base_ad_number,
                "logical_version_key": row.logical_version_key,
                "file_instance_id": row.file_instance_id,
                "content_id": row.content_id,
                "file_name": row.file_name,
                "relative_path": row.relative_path,
                "pdf_sha256": row.file_sha256,
                "manifest_normalized_text_sha256": row.normalized_text_sha256,
                "page_number": page_index,
                "page_count": actual_page_count,
                "extraction_library": "pypdf",
                "extraction_library_version": library_version,
                "extraction_mode": extraction_mode,
                "page_text_sha256": sha256_text(text),
                "text_char_count": len(text),
                "text": text,
            }
            handle.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, output_path)
    verified_pages, verified_chars = parse_page_jsonl(output_path, row)
    if verified_pages != actual_page_count or verified_chars != character_count:
        raise IntegrityError(f"Post-write page JSONL verification failed: {output_path}")
    return actual_page_count, character_count


def build_aggregate_page_jsonl(
    rows: Iterable[SelectionRow], page_dir: Path, output_path: Path
) -> tuple[int, str]:
    temporary = output_path.with_name(output_path.name + ".tmp")
    total_pages = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with temporary.open("w", encoding="utf-8", newline="\n") as output:
        for row in rows:
            source = page_dir / row.page_jsonl_name
            verified_pages, _ = parse_page_jsonl(source, row)
            with source.open("r", encoding="utf-8") as handle:
                for line in handle:
                    output.write(line)
            total_pages += verified_pages
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, output_path)
    return total_pages, sha256_path(output_path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--pdf-dir", type=Path, default=DEFAULT_PDF_DIR)
    parser.add_argument("--page-text-dir", type=Path, default=DEFAULT_PAGE_TEXT_DIR)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--report-csv", type=Path, default=DEFAULT_REPORT_CSV)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="never use the network; fail if any selected PDF is absent",
    )
    parser.add_argument(
        "--rebuild-page-text",
        action="store_true",
        help="replace derived page JSONL files instead of verifying/reusing them",
    )
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--chunk-size-mib", type=int, default=4)
    parser.add_argument(
        "--user-agent",
        default="Capstone-Airbus-AD-Pilot/1.0 (+research source verification)",
    )
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.retries < 1:
        parser.error("--retries must be at least 1")
    if args.chunk_size_mib < 1:
        parser.error("--chunk-size-mib must be at least 1")
    return args


def run(args: argparse.Namespace) -> int:
    selection = args.selection.expanduser().resolve()
    pdf_dir = ensure_safe_output_path(args.pdf_dir, "PDF output directory")
    page_dir = ensure_safe_output_path(args.page_text_dir, "page-text output directory")
    report_json = ensure_safe_output_path(args.report_json, "JSON report")
    report_csv = ensure_safe_output_path(args.report_csv, "CSV report")
    if pdf_dir == page_dir:
        raise RetrievalError("PDF and page-text output directories must be different")

    selection_hash: str | None = None
    report = VerificationReport(
        selection=selection,
        selection_sha256=None,
        pdf_dir=pdf_dir,
        page_dir=page_dir,
        report_json=report_json,
        report_csv=report_csv,
    )
    try:
        selection_hash = selection_file_sha256(selection)
        report.selection_sha256 = selection_hash
        rows = read_selection(selection)
        pdf_dir.mkdir(parents=True, exist_ok=True)
        page_dir.mkdir(parents=True, exist_ok=True)
        document_reports = {
            row.file_instance_id: initial_document_report(row, pdf_dir, page_dir)
            for row in rows
        }
        report.documents = [document_reports[row.file_instance_id] for row in rows]
        report.status = "in_progress"
        report.write()

        mismatches = verify_existing_pdfs(rows, pdf_dir, document_reports)
        report.write()
        if mismatches:
            raise IntegrityError(
                "Existing local PDF integrity failure(s); no downloads were attempted:\n- "
                + "\n- ".join(mismatches)
            )

        opener = urllib.request.build_opener(OfficialEasaRedirectHandler())
        missing_offline: list[str] = []
        for row in rows:
            target = pdf_dir / row.file_name
            item = document_reports[row.file_instance_id]
            try:
                if not target.exists():
                    if args.offline:
                        item["pdf_status"] = "missing_offline"
                        item["error"] = "selected PDF is absent and --offline forbids download"
                        missing_offline.append(row.ad_number)
                        report.write()
                        continue
                    item["pdf_status"] = download_pdf(
                        row,
                        target,
                        opener=opener,
                        timeout=args.timeout,
                        retries=args.retries,
                        chunk_size=args.chunk_size_mib * 1024 * 1024,
                        user_agent=args.user_agent,
                    )
                    item["actual_sha256"] = sha256_path(target)
                    item["pdf_bytes"] = target.stat().st_size
                if item["actual_sha256"] is None:
                    item["actual_sha256"] = sha256_path(target)
                    item["pdf_bytes"] = target.stat().st_size
                if item["actual_sha256"] != row.file_sha256:
                    raise IntegrityError(
                        f"Final SHA-256 mismatch for {row.ad_number}: expected "
                        f"{row.file_sha256}, got {item['actual_sha256']}"
                    )

                page_path = page_dir / row.page_jsonl_name
                if page_path.exists() and not args.rebuild_page_text:
                    actual_pages, character_count = parse_page_jsonl(page_path, row)
                    item["page_text_status"] = "reused_verified"
                else:
                    actual_pages, character_count = extract_page_jsonl(
                        row, target, page_path
                    )
                    item["page_text_status"] = "extracted_verified"
                item["actual_page_count"] = actual_pages
                item["extracted_char_count"] = character_count
                item["page_text_sha256"] = sha256_path(page_path)
                item["error"] = None
            except Exception as exc:
                item["error"] = str(exc)
                if item["pdf_status"] == "pending":
                    item["pdf_status"] = "failed"
                if item["page_text_status"] == "pending":
                    item["page_text_status"] = "failed"
                report.write()
                raise
            report.write()

        if missing_offline:
            raise RetrievalError(
                "Offline run is missing selected PDFs: " + ", ".join(missing_offline)
            )

        aggregate = page_dir / "pilot_pages.jsonl"
        aggregate_pages, aggregate_hash = build_aggregate_page_jsonl(
            rows, page_dir, aggregate
        )
        expected_pages = sum(row.page_count for row in rows)
        if aggregate_pages != expected_pages:
            raise IntegrityError(
                f"Aggregate page count mismatch: expected {expected_pages}, "
                f"found {aggregate_pages}"
            )
        report.aggregate_page_text_file = str(aggregate)
        report.aggregate_page_text_sha256 = aggregate_hash

        summary = report.summary()
        if summary["verified_pdfs"] != EXPECTED_DOCUMENT_COUNT:
            raise IntegrityError(
                f"Expected {EXPECTED_DOCUMENT_COUNT} verified PDFs, "
                f"found {summary['verified_pdfs']}"
            )
        if summary["verified_page_text_files"] != EXPECTED_DOCUMENT_COUNT:
            raise IntegrityError(
                f"Expected {EXPECTED_DOCUMENT_COUNT} verified page-text files, "
                f"found {summary['verified_page_text_files']}"
            )
        report.status = "complete"
        report.completed_at = utc_now()
        report.write()
        print(
            f"Verified {summary['verified_pdfs']} PDFs and "
            f"{summary['verified_pages']} pages."
        )
        print(f"Aggregate JSONL: {aggregate}")
        print(f"Verification report: {report_json}")
        return 0
    except KeyboardInterrupt:
        report.status = "interrupted"
        report.completed_at = utc_now()
        report.fatal_error = "KeyboardInterrupt"
        report.write()
        print("Interrupted; partial downloads and the checkpoint report were preserved.", file=sys.stderr)
        return 130
    except Exception as exc:
        report.status = "failed"
        report.completed_at = utc_now()
        report.fatal_error = str(exc)
        report.write()
        print(f"FAILED: {exc}", file=sys.stderr)
        print(f"Verification report: {report_json}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
