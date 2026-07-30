#!/usr/bin/env python3
"""Build page-delimited, annotation-free inputs for both LLM baselines."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--selection",
        type=Path,
        default=Path("step3_pilot/selection/pilot_selection.json"),
    )
    parser.add_argument(
        "--page-text-dir",
        type=Path,
        default=Path("step3_pilot/page_text"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("step3_pilot/baselines/inputs/pilot_llm_inputs.jsonl"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    if not isinstance(selection, list) or len(selection) != 30:
        raise ValueError("selection must contain exactly 30 rows")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for row in selection:
        source = args.page_text_dir / f"{row['ad_number']}__{row['file_instance_id']}.pages.jsonl"
        pages = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line]
        if len(pages) != int(row["page_count"]):
            raise ValueError(f"{row['ad_number']}: page count mismatch")
        page_payload = [
            {
                "page_number": page["page_number"],
                "page_id": page["page_id"],
                "page_text_sha256": page["page_text_sha256"],
                "text": page["text"],
            }
            for page in pages
        ]
        payload = {
            "input_id": f"{row['ad_number']}__{row['file_instance_id']}",
            "source_document": {
                "file_instance_id": row["file_instance_id"],
                "file_name": row["file_name"],
                "file_sha256": row["file_sha256"],
                "page_count": int(row["page_count"]),
            },
            "pages": page_payload,
            "zero_shot_prompt_version": "zero_shot_v1",
            "schema_guided_prompt_version": "schema_guided_v1",
            "contains_annotation_labels": False,
        }
        payload["input_sha256"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        lines.append(json.dumps(payload, ensure_ascii=False))
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(lines)} annotation-free LLM inputs to {args.output}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
