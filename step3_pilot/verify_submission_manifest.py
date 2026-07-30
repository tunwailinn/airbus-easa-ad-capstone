#!/usr/bin/env python3
"""Verify that the frozen Annotator A/B files have not changed."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("step3_pilot/submitted/submission_manifest.json"),
    )
    parser.add_argument(
        "--submitted-dir", type=Path, default=Path("step3_pilot/submitted")
    )
    parser.add_argument(
        "--selection",
        type=Path,
        default=Path("step3_pilot/selection/pilot_selection.json"),
    )
    parser.add_argument(
        "--roster",
        type=Path,
        default=Path("step3_pilot/selection/annotation_assignment_roster.csv"),
    )
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    errors = []
    if sha256(args.selection) != manifest.get("selection_sha256"):
        errors.append("selection hash changed")
    if sha256(args.roster) != manifest.get("roster_sha256"):
        errors.append("roster hash changed")
    expected_paths = set()
    for row in manifest.get("submissions", []):
        relative = Path(row["stream"]) / row["annotation_file"]
        path = args.submitted_dir / relative
        expected_paths.add(path.resolve())
        if not path.exists():
            errors.append(f"missing {path}")
        elif sha256(path) != row["annotation_sha256"]:
            errors.append(f"hash changed {path}")
    actual_paths = {
        path.resolve()
        for stream in ("annotator_a", "annotator_b")
        for path in (args.submitted_dir / stream).glob("*.annotation.json")
    }
    for path in sorted(actual_paths - expected_paths):
        errors.append(f"unexpected annotation {path}")
    if errors:
        print(f"FAIL frozen submission manifest: {len(errors)} error(s)")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"PASS frozen submission manifest: {len(expected_paths)} unchanged files")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
