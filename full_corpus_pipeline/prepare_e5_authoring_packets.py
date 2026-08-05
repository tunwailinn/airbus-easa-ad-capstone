#!/usr/bin/env python3
"""Build source-grounded authoring packets for E5 benchmark questions.

The default is DEVELOPMENT ONLY. Final-test packets must not be generated during
E5 tuning unless the final benchmark is deliberately being authored/sealed by an
independent review workflow.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from full_corpus_pipeline.document_io import read_page_jsonl
from full_corpus_pipeline.retrieval import section_blocks


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK_ROOT = ROOT / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1"
DEFAULT_PAGE_TEXT_ROOT = ROOT / "data_processed/page_text_v1_1/operational_airbus"


def find_page_file(page_text_root: Path, file_instance_id: str) -> Path:
    pages_dir = page_text_root / "pages"
    matches = list(pages_dir.glob(f"*{file_instance_id}*.pages.jsonl"))
    if len(matches) != 1:
        raise ValueError(
            f"expected one page-text file for {file_instance_id}, found {len(matches)}"
        )
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-root", type=Path, default=DEFAULT_BENCHMARK_ROOT)
    parser.add_argument("--page-text-root", type=Path, default=DEFAULT_PAGE_TEXT_ROOT)
    parser.add_argument(
        "--split",
        choices=["development", "final_test"],
        default="development",
        help="Default is development. Do not open final-test source packets during tuning.",
    )
    args = parser.parse_args()

    split_path = args.benchmark_root / "family_split.csv"
    if not split_path.exists():
        raise FileNotFoundError(
            f"missing E5 family split: {split_path}; run prepare_e5_benchmark_families first"
        )
    frame = pd.read_csv(
        split_path,
        dtype={
            "base_ad_number": str,
            "representative_ad_number": str,
            "representative_file_instance_id": str,
        },
    )
    selected = frame.loc[frame["split"] == args.split].copy()
    if selected.empty:
        raise ValueError(f"no families found for split {args.split}")

    output_dir = args.benchmark_root / "authoring_packets" / args.split
    output_dir.mkdir(parents=True, exist_ok=True)

    total = len(selected)
    for position, row in enumerate(selected.to_dict("records"), 1):
        base_ad = str(row["base_ad_number"])
        file_id = str(row["representative_file_instance_id"])
        print(
            f"[progress] authoring packet {position}/{total}: {base_ad} ({file_id})",
            flush=True,
        )
        page_file = find_page_file(args.page_text_root, file_id)
        pages = read_page_jsonl(page_file)
        blocks = section_blocks(pages)
        packet = {
            "benchmark_version": "easa-airbus-ad-e5-benchmark-v1",
            "split": args.split,
            "base_ad_number": base_ad,
            "representative_ad_number": str(row["representative_ad_number"]),
            "representative_file_instance_id": file_id,
            "representative_relative_path": str(row["representative_relative_path"]),
            "page_text_file": str(page_file),
            "pages": [
                {
                    "page": int(page["page"]),
                    "text": str(page.get("text", "")),
                }
                for page in pages
            ],
            "section_blocks": [
                {
                    "page": int(block["page"]),
                    "section": str(block["section"]),
                    "text": str(block["text"]),
                }
                for block in blocks
            ],
        }
        output_path = output_dir / f"{base_ad}.authoring.json"
        output_path.write_text(
            json.dumps(packet, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    print(
        f"[progress] wrote {total} {args.split} authoring packets to {output_dir}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
