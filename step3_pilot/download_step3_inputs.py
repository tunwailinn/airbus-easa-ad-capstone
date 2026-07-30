#!/usr/bin/env python3
"""Download the current Step 1 metadata needed to build the Step 3 pilot.

The script uses the existing Drive OAuth token in read-only fashion. It never
renames, moves, deletes, or updates files in ``corpus_raw`` or ``metadata``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


METADATA_FILES = {
    "corpus_manifest.csv": "1ggUgqy7oxWmbU2yjvmp55qKSvLI_XI2Q",
    "corpus_manifest.parquet": "129tPjHuMjT1uSMcN266WImbkwTigtJeb",
    "corpus_extracted_text.parquet": "1ROdV5BmGUCY18zqMJyYVjhZdZwmflbAh",
    "near_duplicate_candidates.csv": "1aj_dJW6iXB7DOy6x1F67scXT5VoEyBa-",
    "version_chains.csv": "1mMVDiU1eQnLAosqBBMTsyNMmjQGCOEOl",
    "supersedure_links.csv": "1u_zoGCCvVbPvTNHq3d9SCQuxTfF71ccF",
    "duplicate_review.csv": "1z1r-hEAkjCFubLF50aMTVOZvCBvk_3XA",
    "processing_and_metadata_review.csv": "15kWnlBaejcMPKAkNp74UFYeG1OOAXIgM",
    "manual_overrides.csv": "1iKCosNC18YVbkH4wIkNbN8HgqZmDKgWE",
    "corpus_summary.json": "1Vxm6zBhKFQKgxWOIARKUESNzoKMmqcZ_",
}


def parse_args() -> argparse.Namespace:
    project = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token", type=Path, default=project / "token.json")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "source_metadata",
    )
    parser.add_argument(
        "--force", action="store_true", help="replace already downloaded local copies"
    )
    return parser.parse_args()


def download_file(service, file_id: str, target: Path) -> None:
    request = service.files().get_media(fileId=file_id)
    with target.open("wb") as handle:
        downloader = MediaIoBaseDownload(handle, request, chunksize=8 * 1024 * 1024)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    credentials = Credentials.from_authorized_user_file(str(args.token))
    if not credentials.valid:
        credentials.refresh(Request())
    service = build("drive", "v3", credentials=credentials, cache_discovery=False)

    inventory = []
    for name, file_id in METADATA_FILES.items():
        target = args.output_dir / name
        remote = (
            service.files()
            .get(fileId=file_id, fields="id,name,mimeType,size,modifiedTime,md5Checksum")
            .execute()
        )
        if args.force or not target.exists() or target.stat().st_size != int(remote["size"]):
            download_file(service, file_id, target)
            status = "downloaded"
        else:
            status = "reused"
        inventory.append(
            {
                "local_name": name,
                "drive_file_id": file_id,
                "drive_name": remote["name"],
                "mime_type": remote["mimeType"],
                "size": int(remote["size"]),
                "modified_time": remote["modifiedTime"],
                "md5": remote.get("md5Checksum"),
                "status": status,
            }
        )
        print(f"{status:10} {name} ({int(remote['size']):,} bytes)")

    inventory_path = args.output_dir / "drive_input_inventory.json"
    inventory_path.write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"inventory  {inventory_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
