#!/usr/bin/env python3
"""Download EASA-issued AD PDFs for AIRBUS S.A.S. to Google Drive.

Selenium is used to apply EASA's exact Advanced Search taxonomy filter and to
walk the filtered result pages. PDF files are streamed with requests using the
same browser session cookies, uploaded to Google Drive, and then deleted from
the local temporary directory.

Required packages:
    python3 -m pip install --upgrade \
      selenium requests google-api-python-client google-auth-httplib2 \
      google-auth-oauthlib

Before the first non-dry run, enable the Google Drive API, create an OAuth
Desktop app, and save its downloaded client file as credentials.json beside
this script. Never commit credentials.json or token.json.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import re
import sys
import tempfile
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import requests
from requests.adapters import HTTPAdapter
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from urllib3.util.retry import Retry


BASE_URL = "https://ad.easa.europa.eu"
ADVANCED_SEARCH_URL = f"{BASE_URL}/search/advanced"
RESULTS_URL = f"{BASE_URL}/search/advanced/result"
TC_HOLDER = "AIRBUS S.A.S."
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file"
DRIVE_FOLDER_MIME = "application/vnd.google-apps.folder"
EASA_AD_NUMBER_RE = re.compile(
    r"^\d{4}-\d{4}(?:R\d+)?(?:-CN)?$", flags=re.IGNORECASE
)


@dataclass(frozen=True)
class AdPdf:
    ad_number: str
    issue_date: str
    subject: str
    detail_url: str
    pdf_url: str
    filename: str


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description=(
            "Download EASA AD PDFs filtered to AIRBUS S.A.S. and upload them "
            "to a Google Drive folder."
        )
    )
    parser.add_argument(
        "--credentials",
        type=Path,
        default=script_dir / "credentials.json",
        help="Google OAuth Desktop client JSON (default: %(default)s)",
    )
    parser.add_argument(
        "--token",
        type=Path,
        default=script_dir / "token.json",
        help="OAuth token cache created after first login (default: %(default)s)",
    )
    parser.add_argument(
        "--drive-folder",
        default="EASA Airbus S.A.S. ADs",
        help="Destination folder name in Google Drive (default: %(default)s)",
    )
    parser.add_argument(
        "--drive-parent-id",
        default="root",
        help="Destination parent folder ID, or 'root' (default: %(default)s)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=script_dir / "easa_airbus_ad_manifest.csv",
        help="Local append-only run log (default: %(default)s)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        help="Process only the first N filtered pages; useful for testing",
    )
    parser.add_argument(
        "--page-delay",
        type=float,
        default=1.0,
        help="Seconds to pause between EASA result pages (default: %(default)s)",
    )
    parser.add_argument(
        "--download-delay",
        type=float,
        default=1.0,
        help="Seconds to pause after each EASA PDF request (default: %(default)s)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Concurrent PDF download/upload workers (default: %(default)s)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=40,
        help="Selenium wait timeout in seconds (default: %(default)s)",
    )
    parser.add_argument(
        "--headful",
        action="store_true",
        help="Show Chrome instead of running it headlessly",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List matching PDFs without downloading or using Google Drive",
    )
    args = parser.parse_args()

    if args.max_pages is not None and args.max_pages < 1:
        parser.error("--max-pages must be at least 1")
    if args.page_delay < 0 or args.download_delay < 0:
        parser.error("delays cannot be negative")
    if args.timeout < 1:
        parser.error("--timeout must be at least 1")
    if args.workers < 1 or args.workers > 8:
        parser.error("--workers must be between 1 and 8")
    return args


def build_driver(headful: bool) -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    if not headful:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1200")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=en-GB")
    options.page_load_strategy = "normal"
    return webdriver.Chrome(options=options)


def configure_airbus_ad_filter(
    driver: webdriver.Chrome, wait: WebDriverWait
) -> None:
    driver.get(ADVANCED_SEARCH_URL)

    # Expand the "A" branch. Clicking the letter itself only selects it; the
    # adjacent ExtJS expander loads the holder list.
    a_expander_xpath = (
        "//*[@id='treeTaxonomy']//a[normalize-space(.)='A']/../img["
        "contains(concat(' ', normalize-space(@class), ' '), "
        "' x-tree-ec-icon ')]"
    )
    a_expander = wait.until(
        EC.element_to_be_clickable((By.XPATH, a_expander_xpath))
    )
    if "x-tree-elbow-plus" in (a_expander.get_attribute("class") or ""):
        a_expander.click()

    airbus_xpath = (
        "//*[@id='treeTaxonomy']//a[normalize-space(.)='AIRBUS S.A.S.']"
    )
    airbus = wait.until(EC.element_to_be_clickable((By.XPATH, airbus_xpath)))
    driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
        airbus,
    )
    ActionChains(driver).double_click(airbus).perform()

    current_filter_xpath = (
        "//*[@id='treeFilter']//a[normalize-space(.)='AIRBUS S.A.S.']"
    )
    wait.until(EC.presence_of_element_located((By.XPATH, current_filter_xpath)))

    ad_checkbox = wait.until(EC.element_to_be_clickable((By.ID, "fi_adclass_AD")))
    if not ad_checkbox.is_selected():
        ad_checkbox.click()

    search_xpath = "//*[@id='frmMain']//img[@alt='Search']/parent::a"
    wait.until(EC.element_to_be_clickable((By.XPATH, search_xpath))).click()
    wait.until(EC.url_contains("/search/advanced/result"))
    wait_for_result_page(driver, wait)

    tree_value = driver.find_element(By.ID, "fi_tree").get_attribute("value") or ""
    if TC_HOLDER not in tree_value:
        raise RuntimeError(
            f"EASA result page did not retain the exact {TC_HOLDER!r} filter"
        )


def wait_for_result_page(driver: webdriver.Chrome, wait: WebDriverWait) -> str:
    heading = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h3[contains(normalize-space(.), 'Displaying records')]")
        )
    )
    text = heading.text.strip()
    if "publications" not in text:
        raise RuntimeError(f"Unexpected EASA results heading: {text!r}")
    return text


def result_totals(heading: str) -> tuple[int, int]:
    match = re.search(
        r"Displaying records\s+([\d,]+)\s+to\s+([\d,]+)\s+out of a total "
        r"of\s+([\d,]+)\s+publications",
        heading,
        flags=re.IGNORECASE,
    )
    if not match:
        raise RuntimeError(f"Could not parse EASA results heading: {heading!r}")
    first, last, total = (int(value.replace(",", "")) for value in match.groups())
    page_size = last - first + 1
    if page_size < 1:
        raise RuntimeError(f"Invalid EASA page size parsed from: {heading!r}")
    return total, math.ceil(total / page_size)


def safe_filename_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return cleaned.strip("._") or "unknown"


def filename_from_pdf_url(ad_number: str, pdf_url: str) -> str:
    segments = [unquote(part) for part in urlsplit(pdf_url).path.split("/") if part]
    try:
        blob_index = segments.index("blob")
        blob_name = segments[blob_index + 1]
        attachment_key = segments[blob_index + 2]
    except (ValueError, IndexError) as exc:
        raise ValueError(f"Unexpected EASA blob URL: {pdf_url}") from exc

    filename = "__".join(
        (
            safe_filename_part(ad_number),
            safe_filename_part(attachment_key),
            safe_filename_part(blob_name),
        )
    )
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    if len(filename) > 220:
        filename = filename[:216].rstrip("._") + ".pdf"
    return filename


def is_pdf_blob_url(url: str) -> bool:
    path = unquote(urlsplit(url).path)
    return bool(re.search(r"/blob/[^/]+\.pdf(?:/|$)", path, flags=re.IGNORECASE))


def blob_filename(pdf_url: str) -> str:
    segments = [unquote(part) for part in urlsplit(pdf_url).path.split("/") if part]
    try:
        return segments[segments.index("blob") + 1]
    except (ValueError, IndexError) as exc:
        raise ValueError(f"Unexpected EASA blob URL: {pdf_url}") from exc


def is_easa_issued_pdf(ad_number: str, pdf_url: str) -> bool:
    """Accept current and legacy EASA AD attachment naming conventions.

    Most repository attachments use EASA_AD_. Some older EASA cancellation
    notices use a legacy AD_ prefix, so allow that form only for -CN records.
    The result row's explicit EU issuing-authority flag is checked separately.
    """
    filename = blob_filename(pdf_url).upper()
    return bool(EASA_AD_NUMBER_RE.fullmatch(ad_number)) and (
        filename.startswith("EASA_AD_")
        or (ad_number.upper().endswith("-CN") and filename.startswith("AD_"))
    )


def is_easa_drive_filename(filename: str) -> bool:
    parts = filename.split("__", 2)
    return (
        len(parts) == 3
        and bool(EASA_AD_NUMBER_RE.fullmatch(parts[0]))
        and (
            parts[2].upper().startswith("EASA_AD_")
            or (
                parts[0].upper().endswith("-CN")
                and parts[2].upper().startswith("AD_")
            )
        )
    )


def extract_page_pdfs(
    driver: webdriver.Chrome,
) -> tuple[list[AdPdf], list[str], list[str]]:
    rows = driver.find_elements(
        By.XPATH,
        "//tr[.//a[contains(@href, 'ad.easa.europa.eu/ad/')]]",
    )
    items: list[AdPdf] = []
    rows_without_pdf: list[str] = []
    excluded_non_easa: list[str] = []

    for row in rows:
        ad_link = row.find_element(
            By.XPATH, ".//a[contains(@href, 'ad.easa.europa.eu/ad/')]"
        )
        ad_number = ad_link.text.strip()
        detail_url = ad_link.get_attribute("href")
        cells = row.find_elements(By.TAG_NAME, "td")
        authority_flags = (
            cells[1].find_elements(By.TAG_NAME, "img") if len(cells) > 1 else []
        )
        issued_by = (
            (authority_flags[0].get_attribute("alt") or "").strip().upper()
            if authority_flags
            else ""
        )
        issue_date = cells[2].text.strip() if len(cells) > 2 else ""
        subject = cells[3].text.strip() if len(cells) > 3 else ""

        pdf_urls: list[str] = []
        for link in row.find_elements(By.XPATH, ".//a[contains(@href, '/blob/')]"):
            href = link.get_attribute("href")
            if href and is_pdf_blob_url(href):
                pdf_urls.append(href)

        if not pdf_urls:
            rows_without_pdf.append(ad_number)
            continue

        for pdf_url in dict.fromkeys(pdf_urls):
            if issued_by != "EU":
                excluded_non_easa.append(ad_number)
                continue
            if not is_easa_issued_pdf(ad_number, pdf_url):
                excluded_non_easa.append(ad_number)
                continue
            items.append(
                AdPdf(
                    ad_number=ad_number,
                    issue_date=issue_date,
                    subject=subject,
                    detail_url=detail_url,
                    pdf_url=pdf_url,
                    filename=filename_from_pdf_url(ad_number, pdf_url),
                )
            )
    return items, rows_without_pdf, excluded_non_easa


def build_download_session(driver: webdriver.Chrome) -> requests.Session:
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        status=5,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(("GET",)),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    for cookie in driver.get_cookies():
        session.cookies.set(
            cookie["name"],
            cookie["value"],
            domain=cookie.get("domain"),
            path=cookie.get("path", "/"),
        )
    user_agent = driver.execute_script("return navigator.userAgent")
    session.headers.update(
        {
            "User-Agent": user_agent,
            "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.1",
            "Referer": driver.current_url,
        }
    )
    return session


def clone_download_session(source: requests.Session) -> requests.Session:
    """Create a thread-local copy of the authenticated EASA HTTP session."""
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        status=5,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(("GET",)),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(source.headers)
    session.cookies.update(source.cookies)
    return session


def download_pdf(
    session: requests.Session, item: AdPdf, temp_dir: Path
) -> Path:
    destination = temp_dir / item.filename
    with session.get(item.pdf_url, stream=True, timeout=(20, 180)) as response:
        response.raise_for_status()
        first_bytes = b""
        with destination.open("wb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                if len(first_bytes) < 1024:
                    first_bytes += chunk[: 1024 - len(first_bytes)]
                output.write(chunk)

    if b"%PDF-" not in first_bytes:
        destination.unlink(missing_ok=True)
        raise RuntimeError(
            f"EASA returned non-PDF content for {item.ad_number}: {item.pdf_url}"
        )
    return destination


def get_drive_service(credentials_path: Path, token_path: Path) -> Any:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    if not credentials_path.exists():
        raise FileNotFoundError(
            f"Google OAuth client file not found: {credentials_path}\n"
            "Create a Desktop OAuth client for the Google Drive API and save "
            "the downloaded JSON at that path."
        )

    scopes = [DRIVE_SCOPE]
    credentials = None
    if token_path.exists():
        credentials = Credentials.from_authorized_user_file(str(token_path), scopes)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), scopes
            )
            credentials = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(credentials.to_json(), encoding="utf-8")
        try:
            os.chmod(token_path, 0o600)
        except OSError:
            pass

    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def escape_drive_query(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def get_or_create_drive_folder(
    service: Any, folder_name: str, parent_id: str
) -> str:
    escaped_name = escape_drive_query(folder_name)
    escaped_parent = escape_drive_query(parent_id)
    query = (
        f"name = '{escaped_name}' and mimeType = '{DRIVE_FOLDER_MIME}' and "
        f"'{escaped_parent}' in parents and trashed = false"
    )
    result = (
        service.files()
        .list(
            q=query,
            spaces="drive",
            pageSize=10,
            fields="files(id,name)",
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
        )
        .execute(num_retries=5)
    )
    folders = result.get("files", [])
    if folders:
        return folders[0]["id"]

    metadata = {
        "name": folder_name,
        "mimeType": DRIVE_FOLDER_MIME,
        "parents": [parent_id],
    }
    folder = (
        service.files()
        .create(body=metadata, fields="id", supportsAllDrives=True)
        .execute(num_retries=5)
    )
    return folder["id"]


def list_existing_drive_files(service: Any, folder_id: str) -> dict[str, str]:
    escaped_folder = escape_drive_query(folder_id)
    query = (
        f"'{escaped_folder}' in parents and trashed = false and "
        f"mimeType != '{DRIVE_FOLDER_MIME}'"
    )
    files: dict[str, str] = {}
    page_token = None
    while True:
        response = (
            service.files()
            .list(
                q=query,
                spaces="drive",
                pageSize=1000,
                pageToken=page_token,
                fields="nextPageToken,files(id,name)",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            )
            .execute(num_retries=5)
        )
        for item in response.get("files", []):
            files.setdefault(item["name"], item["id"])
        page_token = response.get("nextPageToken")
        if not page_token:
            return files


def delete_non_easa_drive_files(
    service: Any, existing_files: dict[str, str]
) -> list[str]:
    """Delete third-country and non-AD PDFs from the dedicated app folder."""
    deleted: list[str] = []
    for filename, file_id in list(existing_files.items()):
        if is_easa_drive_filename(filename):
            continue
        (
            service.files()
            .delete(fileId=file_id, supportsAllDrives=True)
            .execute(num_retries=5)
        )
        deleted.append(filename)
        del existing_files[filename]
    return deleted


def upload_pdf(service: Any, folder_id: str, item: AdPdf, path: Path) -> str:
    from googleapiclient.http import MediaFileUpload

    description = (
        f"Source: EASA Safety Publications Tool ({item.detail_url}). "
        "European Union source acknowledged."
    )
    metadata = {
        "name": item.filename,
        "parents": [folder_id],
        "description": description,
        "appProperties": {
            "source": "EASA Safety Publications Tool",
            "adNumber": item.ad_number,
        },
    }
    media = MediaFileUpload(
        str(path), mimetype="application/pdf", resumable=True, chunksize=1024 * 1024
    )
    uploaded = (
        service.files()
        .create(
            body=metadata,
            media_body=media,
            fields="id,name",
            supportsAllDrives=True,
        )
        .execute(num_retries=5)
    )
    return uploaded["id"]


MANIFEST_FIELDS = (
    "timestamp_utc",
    "status",
    "ad_number",
    "issue_date",
    "subject",
    "filename",
    "pdf_url",
    "detail_url",
    "drive_file_id",
    "error",
)


def append_manifest(
    manifest_path: Path,
    item: AdPdf,
    status: str,
    drive_file_id: str = "",
    error: str = "",
) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not manifest_path.exists() or manifest_path.stat().st_size == 0
    with manifest_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS)
        if needs_header:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "status": status,
                "ad_number": item.ad_number,
                "issue_date": item.issue_date,
                "subject": item.subject,
                "filename": item.filename,
                "pdf_url": item.pdf_url,
                "detail_url": item.detail_url,
                "drive_file_id": drive_file_id,
                "error": error[:1000],
            }
        )


def page_url(page_number: int) -> str:
    if page_number == 1:
        return f"{RESULTS_URL}/"
    return f"{RESULTS_URL}/page-{page_number}"


def run(args: argparse.Namespace) -> int:
    drive_service = None
    drive_folder_id = ""
    existing_drive_files: dict[str, str] = {}
    if not args.dry_run:
        drive_service = get_drive_service(args.credentials, args.token)
        drive_folder_id = get_or_create_drive_folder(
            drive_service, args.drive_folder, args.drive_parent_id
        )
        existing_drive_files = list_existing_drive_files(
            drive_service, drive_folder_id
        )
        removed_non_easa = delete_non_easa_drive_files(
            drive_service, existing_drive_files
        )
        if removed_non_easa:
            print(
                f"Removed {len(removed_non_easa)} previously uploaded "
                "out-of-scope PDF(s) from Google Drive:"
            )
            for filename in removed_non_easa:
                print(f"  DELETE {filename}")
        print(
            f"Google Drive folder ready: {args.drive_folder!r} "
            f"({len(existing_drive_files)} existing files)"
        )

    driver = build_driver(args.headful)
    wait = WebDriverWait(driver, args.timeout)
    stats: Counter[str] = Counter()

    try:
        configure_airbus_ad_filter(driver, wait)
        heading = wait_for_result_page(driver, wait)
        total_records, total_pages = result_totals(heading)
        pages_to_process = min(total_pages, args.max_pages or total_pages)
        print(
            f"EASA exact filter {TC_HOLDER!r} + AD: "
            f"{total_records:,} records across {total_pages:,} pages."
        )
        if pages_to_process != total_pages:
            print(f"Test limit active: processing {pages_to_process} page(s).")

        download_session = build_download_session(driver)
        with tempfile.TemporaryDirectory(prefix="easa-airbus-ads-") as temp_name:
            temp_dir = Path(temp_name)
            worker_context = threading.local()

            def download_and_upload(item: AdPdf) -> str:
                if not hasattr(worker_context, "download_session"):
                    worker_context.download_session = clone_download_session(
                        download_session
                    )
                    worker_context.drive_service = get_drive_service(
                        args.credentials, args.token
                    )

                temp_path: Path | None = None
                try:
                    temp_path = download_pdf(
                        worker_context.download_session, item, temp_dir
                    )
                    return upload_pdf(
                        worker_context.drive_service,
                        drive_folder_id,
                        item,
                        temp_path,
                    )
                finally:
                    if temp_path is not None:
                        temp_path.unlink(missing_ok=True)
                    if args.download_delay:
                        time.sleep(args.download_delay)

            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                for page_number in range(1, pages_to_process + 1):
                    target_url = page_url(page_number)
                    if driver.current_url.rstrip("/") != target_url.rstrip("/"):
                        driver.get(target_url)
                    page_heading = wait_for_result_page(driver, wait)
                    items, rows_without_pdf, excluded_non_easa = (
                        extract_page_pdfs(driver)
                    )
                    print(
                        f"Page {page_number}/{pages_to_process}: "
                        f"{len(items)} EASA PDF attachment(s) | {page_heading}"
                    )
                    if excluded_non_easa:
                        unique_excluded = list(dict.fromkeys(excluded_non_easa))
                        print(
                            f"  Excluded {len(excluded_non_easa)} non-EASA-AD "
                            "PDF(s): "
                            + ", ".join(unique_excluded)
                        )
                        stats["excluded_non_easa"] += len(excluded_non_easa)
                    if rows_without_pdf:
                        print(
                            "  Warning: no PDF attachment found for: "
                            + ", ".join(rows_without_pdf)
                        )
                        stats["no_pdf"] += len(rows_without_pdf)

                    pending: list[AdPdf] = []
                    for item in items:
                        if item.filename in existing_drive_files:
                            stats["skipped"] += 1
                            if not args.dry_run:
                                append_manifest(
                                    args.manifest,
                                    item,
                                    "skipped_existing",
                                    existing_drive_files[item.filename],
                                )
                            print(f"  SKIP {item.ad_number}: {item.filename}")
                            continue

                        if args.dry_run:
                            stats["would_upload"] += 1
                            print(f"  PDF  {item.ad_number}: {item.pdf_url}")
                            continue

                        pending.append(item)

                    futures = {
                        executor.submit(download_and_upload, item): item
                        for item in pending
                    }
                    for future in as_completed(futures):
                        item = futures[future]
                        try:
                            drive_file_id = future.result()
                            existing_drive_files[item.filename] = drive_file_id
                            append_manifest(
                                args.manifest, item, "uploaded", drive_file_id
                            )
                            stats["uploaded"] += 1
                            print(f"  OK   {item.ad_number}: {item.filename}")
                        except Exception as exc:  # A later run can retry failures.
                            stats["failed"] += 1
                            append_manifest(
                                args.manifest, item, "failed", error=str(exc)
                            )
                            print(
                                f"  FAIL {item.ad_number}: {exc}",
                                file=sys.stderr,
                            )

                    if page_number < pages_to_process and args.page_delay:
                        time.sleep(args.page_delay)
    except TimeoutException as exc:
        print(
            "Timed out while waiting for the EASA search interface. "
            "Retry with --headful to inspect the page.",
            file=sys.stderr,
        )
        raise RuntimeError("EASA Selenium wait timed out") from exc
    finally:
        driver.quit()

    summary = ", ".join(f"{key}={value}" for key, value in sorted(stats.items()))
    print(f"Finished: {summary or 'no matching PDF attachments'}")
    return 1 if stats["failed"] else 0


def main() -> int:
    args = parse_args()
    try:
        return run(args)
    except KeyboardInterrupt:
        print("\nStopped. Rerun the same command to resume from Google Drive.")
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
