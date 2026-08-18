#!/usr/bin/env python3
"""Validate the locked U5/U6 unseen permanent-ingestion result before U7.

This gate binds the four preserved U5/U6 result artifacts by SHA-256, rechecks
the automatic safeguard counts, validates the isolated E4/E5-C derivative, and
compares the five appended documents against the frozen E4 strict section-chunk
policy. A chunk-policy mismatch does not rewrite the U5/U6 result; it blocks U7
until an explicitly labelled E5-compatible derivative is created.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from full_corpus_pipeline.build_retrieval_experiments import strict_section_chunk_pages
from full_corpus_pipeline.document_io import read_pdf_pages
from full_corpus_pipeline.e5c_retrieval import QwenDenseStore
from full_corpus_pipeline.retrieval import HybridIndex


ROOT = Path(__file__).resolve().parents[2]
UNSEEN_ROOT = ROOT / "evaluation_sets/unseen_incoming_5_v1"
DEFAULT_LOCK = UNSEEN_ROOT / "unseen_permanent_ingestion_result_lock.json"
DEFAULT_COMPATIBILITY_REPORT = (
    ROOT
    / "data_processed/evaluations/unseen_5/permanent_ingestion/"
    / "e5_chunk_policy_compatibility.json"
)
VALIDATOR_VERSION = "unseen-5-permanent-ingestion-result-validator-v1.0"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rooted(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def require_hash(path: Path, expected: str, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f"{label} SHA-256 mismatch: expected {expected}, found {actual}")


def _validate_temp_dependency() -> None:
    subprocess.run(
        [sys.executable, "-m", "full_corpus_pipeline.layer_c.validate_unseen_temporary_result_lock"],
        cwd=ROOT,
        check=True,
    )


def _compact_chunk(chunk: Any) -> dict[str, Any]:
    value = asdict(chunk)
    return {
        "chunk_id": value["chunk_id"],
        "file_instance_id": value["file_instance_id"],
        "ad_number": value["ad_number"],
        "source_pdf": value["source_pdf"],
        "page_start": int(value["page_start"]),
        "page_end": int(value["page_end"]),
        "section": value["section"],
        "text": value["text"],
        "lifecycle_status": value["lifecycle_status"],
    }


def _chunk_policy_compatibility(
    *, index: HybridIndex, store_dir: Path, selected_ads: list[str]
) -> dict[str, Any]:
    manifest_path = store_dir / "extraction_manifest.parquet"
    lifecycle_path = store_dir / "lifecycle_manifest.parquet"
    if not manifest_path.is_file() or not lifecycle_path.is_file():
        raise FileNotFoundError("isolated ingestion manifests are missing")
    manifest = pd.read_parquet(manifest_path)
    lifecycle = pd.read_parquet(lifecycle_path)
    if len(manifest) != 5 or len(lifecycle) != 5:
        raise ValueError("isolated ingestion manifests must contain exactly five rows")

    actual_by_file: dict[str, list[Any]] = {}
    for chunk in index.chunks:
        actual_by_file.setdefault(str(chunk.file_instance_id), []).append(chunk)

    rows: list[dict[str, Any]] = []
    all_exact = True
    for ad_number in selected_ads:
        matches = manifest[manifest["ad_number"].astype(str).str.casefold() == ad_number.casefold()]
        if len(matches) != 1:
            raise ValueError(f"expected exactly one isolated manifest row for {ad_number}")
        manifest_row = matches.iloc[0]
        file_id = str(manifest_row["file_instance_id"])
        source_pdf_name = str(manifest_row["source_pdf"])
        pdf_path = store_dir / "source_pdfs" / source_pdf_name
        if not pdf_path.is_file():
            raise FileNotFoundError(pdf_path)
        lifecycle_rows = lifecycle[lifecycle["file_instance_id"].astype(str) == file_id]
        if len(lifecycle_rows) != 1:
            raise ValueError(f"expected exactly one lifecycle row for {ad_number}")
        lifecycle_status = (
            "operational"
            if bool(lifecycle_rows.iloc[0]["operational_selection"])
            else "historical"
        )
        pages = read_pdf_pages(pdf_path)
        expected = strict_section_chunk_pages(
            pages,
            file_instance_id=file_id,
            ad_number=ad_number,
            source_pdf=source_pdf_name,
            lifecycle_status=lifecycle_status,
        )
        actual = actual_by_file.get(file_id, [])
        expected_compact = [_compact_chunk(chunk) for chunk in expected]
        actual_compact = [_compact_chunk(chunk) for chunk in actual]
        exact = expected_compact == actual_compact
        all_exact = all_exact and exact
        expected_ids = [item["chunk_id"] for item in expected_compact]
        actual_ids = [item["chunk_id"] for item in actual_compact]
        rows.append(
            {
                "ad_number": ad_number,
                "file_instance_id": file_id,
                "strict_expected_chunk_count": len(expected_compact),
                "isolated_actual_chunk_count": len(actual_compact),
                "exact_frozen_e4_chunk_policy_match": exact,
                "expected_chunk_ids": expected_ids,
                "actual_chunk_ids": actual_ids,
                "first_mismatch_index": next(
                    (
                        position
                        for position, (left, right) in enumerate(
                            zip(expected_compact, actual_compact), 1
                        )
                        if left != right
                    ),
                    None,
                ),
            }
        )
    return {
        "version": "unseen-5-e5-chunk-policy-compatibility-v1.0",
        "strict_chunk_policy": "rag-index-build-v1.2 E4 strict_section_chunk_pages",
        "selected_document_count": len(selected_ads),
        "exact_match_count": sum(
            bool(row["exact_frozen_e4_chunk_policy_match"]) for row in rows
        ),
        "all_exact": all_exact,
        "rows": rows,
        "policy": (
            "Diagnostic gate before U7. A mismatch does not alter the preserved U5/U6 "
            "technical-safeguard result; it blocks post-ingestion E5-D evaluation until an "
            "E5-compatible isolated derivative is created and separately audited."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument(
        "--compatibility-report",
        type=Path,
        default=DEFAULT_COMPATIBILITY_REPORT,
    )
    args = parser.parse_args()

    _validate_temp_dependency()
    if not args.lock.is_file():
        raise FileNotFoundError(args.lock)
    lock = json.loads(args.lock.read_text(encoding="utf-8"))
    if lock.get("lock_version") != "unseen-5-permanent-ingestion-result-lock-v1.0":
        raise ValueError("unexpected U5/U6 result lock version")
    if lock.get("status") != "automatic_safeguards_passed_and_locked":
        raise ValueError("U5/U6 automatic safeguards are not locked as passed")

    artifacts = lock.get("local_artifacts") or {}
    for path_key, hash_key, label in (
        ("run_manifest_path", "run_manifest_sha256", "U5/U6 run manifest"),
        ("summary_path", "summary_sha256", "U5/U6 summary"),
        ("events_path", "events_sha256", "U5/U6 events"),
        ("review_packet_path", "review_packet_sha256", "U5/U6 review packet"),
    ):
        require_hash(rooted(str(artifacts[path_key])), str(artifacts[hash_key]), label)

    summary_path = rooted(str(artifacts["summary_path"]))
    manifest_path = rooted(str(artifacts["run_manifest_path"]))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    run_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = lock.get("automatic_result") or {}
    count_fields = (
        "processed_count",
        "ingestion_success_count",
        "ad_identity_match_count",
        "parser_version_match_count",
        "deterministic_record_match_count",
        "copied_source_hash_match_count",
        "index_append_pass_count",
        "e5c_alignment_pass_count",
        "duplicate_rejection_pass_count",
        "lifecycle_decision_count",
        "human_lifecycle_review_required_count",
    )
    for key in count_fields:
        if int(summary.get(key, -1)) != int(expected[key]):
            raise ValueError(f"U5/U6 summary {key} differs from locked result")
    for key in (
        "frozen_e4_unchanged",
        "frozen_e5c_unchanged",
        "normal_data_incoming_unchanged",
        "automatic_safeguards_pass",
    ):
        if bool(summary.get(key)) is not bool(expected[key]):
            raise ValueError(f"U5/U6 summary {key} differs from locked result")
    if run_manifest.get("summary_sha256") != artifacts["summary_sha256"]:
        raise ValueError("U5/U6 run manifest does not bind the locked summary")
    if run_manifest.get("events_sha256") != artifacts["events_sha256"]:
        raise ValueError("U5/U6 run manifest does not bind the locked events")
    if run_manifest.get("review_packet_sha256") != artifacts["review_packet_sha256"]:
        raise ValueError("U5/U6 run manifest does not bind the locked review packet")
    if run_manifest.get("permanent_ingestion_isolated") is not True:
        raise ValueError("U5/U6 run was not isolated")
    if run_manifest.get("frozen_source_indexes_modified") is not False:
        raise ValueError("U5/U6 run reports frozen-source index modification")

    index_dir = rooted(str(lock["next_stage"]["required_index"]))
    dense_dir = rooted(str(lock["next_stage"]["required_e5c_dense"]))
    index = HybridIndex(index_dir)
    config = json.loads(index.config_path.read_text(encoding="utf-8"))
    expected_post_count = int(expected["post_ingestion_chunk_count"])
    if len(index.chunks) != expected_post_count:
        raise ValueError(
            f"isolated E4 chunk count mismatch: expected {expected_post_count}, found {len(index.chunks)}"
        )
    if int(config.get("chunk_count", -1)) != expected_post_count:
        raise ValueError("isolated E4 index_config chunk count mismatch")
    selected_ads = [str(value) for value in lock.get("selected_ads", [])]
    present_ads = {str(chunk.ad_number).casefold() for chunk in index.chunks}
    missing_ads = [ad for ad in selected_ads if ad.casefold() not in present_ads]
    if missing_ads:
        raise ValueError(f"isolated E4 index is missing ingested ADs: {missing_ads}")

    dense = QwenDenseStore(dense_dir, chunk_path=index.chunk_path, chunks=index.chunks)
    if int(dense.embeddings.shape[0]) != int(expected["post_ingestion_e5c_row_count"]):
        raise ValueError("isolated E5-C row count differs from locked U5/U6 result")

    store_dir = summary_path.parent / "isolated_store"
    compatibility = _chunk_policy_compatibility(
        index=index,
        store_dir=store_dir,
        selected_ads=selected_ads,
    )
    args.compatibility_report.parent.mkdir(parents=True, exist_ok=True)
    args.compatibility_report.write_text(
        json.dumps(compatibility, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    output = {
        "validator_version": VALIDATOR_VERSION,
        "status": "valid" if compatibility["all_exact"] else "u5_u6_valid_but_u7_blocked",
        "u5_u6_automatic_safeguards_pass": True,
        "processed_count": 5,
        "post_ingestion_chunk_count": len(index.chunks),
        "post_ingestion_e5c_row_count": int(dense.embeddings.shape[0]),
        "strict_e5_chunk_policy_match_count": compatibility["exact_match_count"],
        "strict_e5_chunk_policy_all_exact": compatibility["all_exact"],
        "compatibility_report": str(args.compatibility_report),
        "u7_allowed": bool(compatibility["all_exact"]),
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0 if compatibility["all_exact"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
