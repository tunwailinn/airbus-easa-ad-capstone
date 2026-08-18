#!/usr/bin/env python3
"""Evaluate permanent ingestion of the five frozen unseen PDFs in isolation.

U5/U6 begins only after the human-approved U3/U4 temporary-document result lock
validates. The evaluator clones the frozen E4/BM25 substrate and frozen E5-C Qwen
dense store into an isolated evaluation workspace, ingests each held-out PDF once,
then immediately retries the exact same PDF to verify SHA-256 duplicate rejection.

The frozen source indexes and normal data_incoming store are read-only audit
references. No hosted QA is called and no model is retrained.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from full_corpus_pipeline.build_e5c_dense_embeddings import (
    BUILD_VERSION as E5C_BUILD_VERSION,
    MODEL_NAME as E5C_MODEL,
    MODEL_REVISION as E5C_REVISION,
    sha256_file,
)
from full_corpus_pipeline.document_io import file_sha256, read_pdf_pages
from full_corpus_pipeline.e5c_dense_append import append_e5c_dense_isolated
from full_corpus_pipeline.e5c_retrieval import QwenDenseStore
from full_corpus_pipeline.local_extractor_v216 import PARSER_VERSION
from full_corpus_pipeline.permanent_ingest import ingest_pdf, load_sidecar
from full_corpus_pipeline.retrieval import HybridIndex, chunk_pages


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SELECTION = ROOT / "evaluation_sets/unseen_incoming_5_v1/selection.csv"
DEFAULT_PREPARATION = ROOT / "data_processed/evaluations/unseen_5/preparation"
DEFAULT_CORPUS_MANIFEST = ROOT / "step3_pilot/source_metadata/corpus_manifest.parquet"
DEFAULT_E4_INDEX = ROOT / "data_processed/indexes/rag_v1_2/e4_section_hybrid"
DEFAULT_E5C_DENSE = ROOT / "data_processed/indexes/e5c_qwen3_embedding_0_6b"
DEFAULT_NORMAL_STORE = ROOT / "data_incoming"
DEFAULT_OUTPUT = ROOT / "data_processed/evaluations/unseen_5/permanent_ingestion"
EVALUATOR_VERSION = "unseen-5-permanent-ingestion-eval-v1.0"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_fingerprint(path: Path) -> dict[str, str]:
    path = Path(path)
    if not path.exists():
        return {}
    return {
        str(item.relative_to(path)): sha256(item)
        for item in sorted(path.rglob("*"))
        if item.is_file()
    }


def jsonl_write(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def count_parquet(path: Path) -> int:
    frame = load_sidecar(path)
    return 0 if frame.empty else len(frame)


def load_packet(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_lock_validator() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "full_corpus_pipeline.layer_c.validate_unseen_temporary_result_lock"],
        cwd=ROOT,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("U3/U4 temporary result lock did not validate; permanent ingestion is blocked")


def _ensure_outside(source: Path, destination: Path, label: str) -> None:
    source = source.resolve()
    destination = destination.resolve()
    if destination == source or source in destination.parents:
        raise ValueError(f"{label} destination must not be inside the frozen source artifact")


def _validate_source_artifacts(e4_dir: Path, e5c_dir: Path) -> dict[str, Any]:
    e4_config_path = e4_dir / "index_config.json"
    e4_chunks_path = e4_dir / "chunks.jsonl"
    e5c_meta_path = e5c_dir / "metadata.json"
    e5c_embeddings_path = e5c_dir / "dense_embeddings.npy"
    for path in (e4_config_path, e4_chunks_path, e5c_meta_path, e5c_embeddings_path):
        if not path.is_file():
            raise FileNotFoundError(path)

    e4_config = json.loads(e4_config_path.read_text(encoding="utf-8"))
    if e4_config.get("dense_backend") != "sentence_transformers":
        raise ValueError("frozen E4 substrate is not sentence_transformers-backed")
    if e4_config.get("dense_index_backend") != "faiss_index_flat_ip":
        raise ValueError("frozen E4 substrate is not FAISS IndexFlatIP")
    e4_count = sum(1 for line in e4_chunks_path.read_text(encoding="utf-8").splitlines() if line.strip())
    if int(e4_config.get("chunk_count", -1)) != e4_count:
        raise ValueError("frozen E4 config/chunk count mismatch")

    e5c_meta = json.loads(e5c_meta_path.read_text(encoding="utf-8"))
    if e5c_meta.get("build_version") != E5C_BUILD_VERSION:
        raise ValueError("unexpected frozen E5-C build version")
    if e5c_meta.get("model") != E5C_MODEL or e5c_meta.get("model_revision") != E5C_REVISION:
        raise ValueError("unexpected frozen E5-C model/revision")
    if e5c_meta.get("chunk_source_sha256") != sha256_file(e4_chunks_path):
        raise ValueError("frozen E5-C store is not aligned to frozen E4 chunks")
    embeddings = np.load(e5c_embeddings_path, mmap_mode="r")
    if embeddings.ndim != 2 or int(embeddings.shape[0]) != e4_count:
        raise ValueError("frozen E5-C embedding row count mismatch")
    return {
        "e4_chunk_count": e4_count,
        "e4_embedding_model": e4_config.get("embedding_model"),
        "e5c_chunk_count": int(e5c_meta.get("chunk_count", -1)),
        "e5c_model": E5C_MODEL,
        "e5c_revision": E5C_REVISION,
    }


def _record_signals(record: dict[str, Any]) -> dict[str, Any]:
    identity = record.get("ad_identity") or {}
    supersedure = record.get("supersedure") or {}
    return {
        "correction_date": identity.get("correction_date"),
        "correction_statement": identity.get("correction_statement"),
        "revision": identity.get("revision"),
        "revision_statement": identity.get("revision_statement"),
        "superseded_ad_numbers": list(supersedure.get("superseded_ad_numbers") or []),
        "supersedure_statement": supersedure.get("statement"),
    }


def _build_review_packet(path: Path, rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    lines = [
        "# Five-PDF Unseen Permanent-Ingestion Review Packet",
        "",
        f"Evaluator: `{EVALUATOR_VERSION}`",
        "",
        "## Automatic safeguards",
        "",
        f"- Ingestion successes: **{summary['ingestion_success_count']}/5**",
        f"- Exact duplicate rejections: **{summary['duplicate_rejection_pass_count']}/5**",
        f"- Deterministic record matches: **{summary['deterministic_record_match_count']}/5**",
        f"- Isolated E4 append checks: **{summary['index_append_pass_count']}/5**",
        f"- Isolated E5-C alignment checks: **{summary['e5c_alignment_pass_count']}/5**",
        f"- Frozen source E4 unchanged: **{summary['frozen_e4_unchanged']}**",
        f"- Frozen source E5-C unchanged: **{summary['frozen_e5c_unchanged']}**",
        f"- Normal `data_incoming/` unchanged: **{summary['normal_data_incoming_unchanged']}**",
        "",
        "## Lifecycle observations",
        "",
        "| Stratum | AD | relationship_status | operational | correction | revision statement | superseded ADs |",
        "|---|---|---|---:|---|---|---|",
    ]
    for row in rows:
        sig = row.get("record_signals") or {}
        lifecycle = row.get("lifecycle") or {}
        lines.append(
            "| {stratum} | {ad} | {rel} | {op} | {corr} | {rev} | {sup} |".format(
                stratum=row.get("stratum"),
                ad=row.get("selected_ad_number"),
                rel=lifecycle.get("relationship_status", ""),
                op=str(bool(lifecycle.get("operational_selection"))),
                corr=sig.get("correction_date") or sig.get("correction_statement") or "—",
                rev=(sig.get("revision_statement") or "—").replace("|", "/"),
                sup=", ".join(sig.get("superseded_ad_numbers") or []) or "—",
            )
        )
    lines.extend(
        [
            "",
            "## Human-review boundary",
            "",
            "The lifecycle engine is revision-family based. Correction and supersedure signals are preserved in the extracted content record but are not automatically promoted into cross-family operational lifecycle decisions. Review ambiguous decisions as safeguards, not as silently corrected labels.",
            "",
            "Do not modify the frozen E5 artifacts based on these observations. Any later architecture change is post-hoc engineering work.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--preparation-dir", type=Path, default=DEFAULT_PREPARATION)
    parser.add_argument("--corpus-manifest", type=Path, default=DEFAULT_CORPUS_MANIFEST)
    parser.add_argument("--source-e4-index", type=Path, default=DEFAULT_E4_INDEX)
    parser.add_argument("--source-e5c-dense", type=Path, default=DEFAULT_E5C_DENSE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--qwen-device", default="auto")
    parser.add_argument("--qwen-batch-size", type=int, default=8)
    parser.add_argument("--confirm-run", action="store_true")
    args = parser.parse_args()

    if not args.confirm_run:
        raise SystemExit("U5/U6 isolated permanent-ingestion evaluation requires --confirm-run")
    _run_lock_validator()

    for path in (args.selection, args.corpus_manifest, args.preparation_dir / "preparation_manifest.json"):
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise ValueError(f"refusing to overwrite non-empty U5/U6 output: {args.output_dir}")

    clone_e4 = args.output_dir / "isolated_index/e4_section_hybrid"
    clone_e5c = args.output_dir / "isolated_index/e5c_qwen3_embedding_0_6b"
    store_dir = args.output_dir / "isolated_store"
    _ensure_outside(args.source_e4_index, clone_e4, "E4 clone")
    _ensure_outside(args.source_e5c_dense, clone_e5c, "E5-C clone")

    source_validation = _validate_source_artifacts(args.source_e4_index, args.source_e5c_dense)
    source_e4_before = tree_fingerprint(args.source_e4_index)
    source_e5c_before = tree_fingerprint(args.source_e5c_dense)
    normal_store_before = tree_fingerprint(DEFAULT_NORMAL_STORE)

    print("[progress] cloning frozen E4 substrate into isolated evaluation index", flush=True)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    clone_e4.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(args.source_e4_index, clone_e4)
    print("[progress] cloning frozen E5-C Qwen dense store", flush=True)
    shutil.copytree(args.source_e5c_dense, clone_e5c)

    if tree_fingerprint(clone_e4) != source_e4_before:
        raise ValueError("isolated E4 clone differs from frozen source before ingestion")
    if tree_fingerprint(clone_e5c) != source_e5c_before:
        raise ValueError("isolated E5-C clone differs from frozen source before ingestion")

    selection = pd.read_csv(args.selection, dtype={"file_instance_id": str, "ad_number": str})
    if len(selection) != 5 or selection["file_instance_id"].nunique() != 5:
        raise ValueError("U5/U6 requires exactly five distinct frozen selection rows")
    prep_rows = json.loads((args.preparation_dir / "preparation_manifest.json").read_text(encoding="utf-8"))
    prep_by_id = {str(row["file_instance_id"]): row for row in prep_rows}
    if len(prep_by_id) != 5:
        raise ValueError("preparation manifest does not contain five unique file IDs")

    events_path = args.output_dir / "ingestion_events.jsonl"
    results: list[dict[str, Any]] = []
    aborted = False

    for position, selected in enumerate(selection.to_dict(orient="records"), 1):
        selected_id = str(selected["file_instance_id"])
        selected_ad = str(selected["ad_number"])
        stratum = str(selected["stratum"])
        prep = prep_by_id.get(selected_id)
        if prep is None:
            raise ValueError(f"missing preparation row for {selected_id}")
        pdf_path = Path(str(prep["source_pdf"]))
        packet_path = Path(str(prep["authoring_packet"]))
        if not pdf_path.is_file() or not packet_path.is_file():
            raise FileNotFoundError(pdf_path if not pdf_path.is_file() else packet_path)
        if file_sha256(pdf_path) != str(selected["file_sha256"]):
            raise ValueError(f"source hash mismatch before U5 ingest: {selected_ad}")
        packet = load_packet(packet_path)
        expected_record = (packet.get("frozen_extraction") or {}).get("record")

        print(f"[progress] U5/U6 ingest {position}/5: {selected_ad} ({stratum})", flush=True)
        before_config = json.loads((clone_e4 / "index_config.json").read_text(encoding="utf-8"))
        before_count = int(before_config["chunk_count"])
        before_e5c = json.loads((clone_e5c / "metadata.json").read_text(encoding="utf-8"))
        before_e5c_count = int(before_e5c["chunk_count"])
        before_extract_rows = count_parquet(store_dir / "extraction_manifest.parquet")
        before_lifecycle_rows = count_parquet(store_dir / "lifecycle_manifest.parquet")

        event: dict[str, Any] = {
            "position": position,
            "stratum": stratum,
            "selected_ad_number": selected_ad,
            "selected_file_instance_id": selected_id,
            "selected_source_sha256": str(selected["file_sha256"]),
            "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        try:
            result = ingest_pdf(
                pdf_path,
                corpus_manifest=args.corpus_manifest,
                store_dir=store_dir,
                index_dir=clone_e4,
                allow_dense_fallback=False,
                held_out_selection=args.selection,
            )
            record_path = Path(str(result["record"]))
            record = json.loads(record_path.read_text(encoding="utf-8"))
            record_match = record == expected_record
            copied_source_hash_match = file_sha256(Path(str(result["source_pdf"]))) == str(selected["file_sha256"])
            ad_match = str(result["ad_number"]).casefold() == selected_ad.casefold()
            parser_match = str(result["parser_version"]) == PARSER_VERSION

            lifecycle = result["lifecycle"]
            pages = read_pdf_pages(Path(str(result["source_pdf"])))
            appended_chunks = chunk_pages(
                pages,
                file_instance_id=str(result["file_instance_id"]),
                ad_number=str(result["ad_number"]),
                source_pdf=Path(str(result["source_pdf"])).name,
                lifecycle_status="operational" if lifecycle["operational_selection"] else "historical",
            )
            after_config = json.loads((clone_e4 / "index_config.json").read_text(encoding="utf-8"))
            after_count = int(after_config["chunk_count"])
            index_append_pass = (
                after_count - before_count == len(appended_chunks)
                and int((result.get("index_append") or {}).get("added_chunk_count", -1)) == len(appended_chunks)
            )

            e5c_append = append_e5c_dense_isolated(
                dense_dir=clone_e5c,
                index_dir=clone_e4,
                chunks=appended_chunks,
                device=args.qwen_device,
                batch_size=args.qwen_batch_size,
            )
            after_e5c_count = int(e5c_append["chunk_count"])
            e5c_alignment_pass = (
                before_e5c_count == before_count
                and after_e5c_count == after_count
                and e5c_append.get("chunk_source_sha256") == sha256_file(clone_e4 / "chunks.jsonl")
            )
            # Constructor validation checks build/model/revision, source SHA, row order and dimensions.
            isolated_index = HybridIndex(clone_e4)
            QwenDenseStore(
                clone_e5c,
                chunk_path=isolated_index.chunk_path,
                chunks=isolated_index.chunks,
            )

            extract_rows_after_first = count_parquet(store_dir / "extraction_manifest.parquet")
            lifecycle_rows_after_first = count_parquet(store_dir / "lifecycle_manifest.parquet")
            duplicate_rejected = False
            duplicate_error = None
            try:
                ingest_pdf(
                    pdf_path,
                    corpus_manifest=args.corpus_manifest,
                    store_dir=store_dir,
                    index_dir=clone_e4,
                    allow_dense_fallback=False,
                    held_out_selection=args.selection,
                )
            except ValueError as exc:
                duplicate_error = str(exc)
                duplicate_rejected = "exact duplicate rejected" in duplicate_error
            duplicate_no_mutation = (
                count_parquet(store_dir / "extraction_manifest.parquet") == extract_rows_after_first
                and count_parquet(store_dir / "lifecycle_manifest.parquet") == lifecycle_rows_after_first
                and int(json.loads((clone_e4 / "index_config.json").read_text(encoding="utf-8"))["chunk_count"]) == after_count
                and int(json.loads((clone_e5c / "metadata.json").read_text(encoding="utf-8"))["chunk_count"]) == after_e5c_count
            )

            event.update(
                {
                    "status": "success",
                    "incoming_file_instance_id": result["file_instance_id"],
                    "ad_identity_match": ad_match,
                    "parser_version_match": parser_match,
                    "deterministic_record_match": record_match,
                    "copied_source_hash_match": copied_source_hash_match,
                    "record_signals": _record_signals(record),
                    "lifecycle": lifecycle,
                    "index_before_chunk_count": before_count,
                    "index_added_chunk_count": len(appended_chunks),
                    "index_after_chunk_count": after_count,
                    "index_append_pass": index_append_pass,
                    "index_append_mode": (result.get("index_append") or {}).get("append_mode"),
                    "e5c_before_chunk_count": before_e5c_count,
                    "e5c_after_chunk_count": after_e5c_count,
                    "e5c_alignment_pass": e5c_alignment_pass,
                    "duplicate_rejected": duplicate_rejected,
                    "duplicate_error": duplicate_error,
                    "duplicate_no_mutation": duplicate_no_mutation,
                    "extraction_manifest_row_delta": extract_rows_after_first - before_extract_rows,
                    "lifecycle_manifest_row_delta": lifecycle_rows_after_first - before_lifecycle_rows,
                }
            )
        except Exception as exc:
            event.update(
                {
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            aborted = True

        event["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        results.append(event)
        jsonl_write(events_path, event)
        if aborted:
            print(f"[progress] U5/U6 aborted after {selected_ad}: {event.get('error')}", flush=True)
            break

    source_e4_after = tree_fingerprint(args.source_e4_index)
    source_e5c_after = tree_fingerprint(args.source_e5c_dense)
    normal_store_after = tree_fingerprint(DEFAULT_NORMAL_STORE)

    successful = [row for row in results if row.get("status") == "success"]
    summary = {
        "evaluator_version": EVALUATOR_VERSION,
        "status": "completed" if len(successful) == 5 else "completed_with_failure",
        "started_from_human_approved_temporary_lock": True,
        "selection_count": 5,
        "processed_count": len(results),
        "ingestion_success_count": len(successful),
        "ad_identity_match_count": sum(bool(row.get("ad_identity_match")) for row in successful),
        "parser_version_match_count": sum(bool(row.get("parser_version_match")) for row in successful),
        "deterministic_record_match_count": sum(bool(row.get("deterministic_record_match")) for row in successful),
        "copied_source_hash_match_count": sum(bool(row.get("copied_source_hash_match")) for row in successful),
        "index_append_pass_count": sum(bool(row.get("index_append_pass")) for row in successful),
        "e5c_alignment_pass_count": sum(bool(row.get("e5c_alignment_pass")) for row in successful),
        "duplicate_rejection_pass_count": sum(
            bool(row.get("duplicate_rejected")) and bool(row.get("duplicate_no_mutation"))
            for row in successful
        ),
        "lifecycle_decision_count": sum(bool(row.get("lifecycle")) for row in successful),
        "human_lifecycle_review_required_count": sum(
            str((row.get("lifecycle") or {}).get("relationship_status", "")).startswith("ambiguous_")
            for row in successful
        ),
        "frozen_e4_unchanged": source_e4_after == source_e4_before,
        "frozen_e5c_unchanged": source_e5c_after == source_e5c_before,
        "normal_data_incoming_unchanged": normal_store_after == normal_store_before,
        "source_validation": source_validation,
        "isolated_store": str(store_dir),
        "isolated_e4_index": str(clone_e4),
        "isolated_e5c_dense": str(clone_e5c),
        "hosted_qa_called": False,
        "model_retrained": False,
        "policy": (
            "Post-final U5/U6 ingestion evaluation only. Frozen E4/E5-C artifacts and the normal data_incoming store are read-only. "
            "Lifecycle ambiguities are reported, not silently corrected or tuned from held-out outcomes."
        ),
        "rows": results,
    }
    summary["automatic_safeguards_pass"] = all(
        [
            summary["ingestion_success_count"] == 5,
            summary["ad_identity_match_count"] == 5,
            summary["parser_version_match_count"] == 5,
            summary["deterministic_record_match_count"] == 5,
            summary["copied_source_hash_match_count"] == 5,
            summary["index_append_pass_count"] == 5,
            summary["e5c_alignment_pass_count"] == 5,
            summary["duplicate_rejection_pass_count"] == 5,
            summary["lifecycle_decision_count"] == 5,
            summary["frozen_e4_unchanged"],
            summary["frozen_e5c_unchanged"],
            summary["normal_data_incoming_unchanged"],
        ]
    )

    summary_path = args.output_dir / "permanent_ingestion_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    review_path = args.output_dir / "lifecycle_review_packet.md"
    _build_review_packet(review_path, successful, summary)
    manifest = {
        "evaluator_version": EVALUATOR_VERSION,
        "selection_sha256": sha256(args.selection),
        "preparation_manifest_sha256": sha256(args.preparation_dir / "preparation_manifest.json"),
        "source_e4_fingerprint_sha256": hashlib.sha256(
            json.dumps(source_e4_before, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "source_e5c_fingerprint_sha256": hashlib.sha256(
            json.dumps(source_e5c_before, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "events_sha256": sha256(events_path),
        "summary_sha256": sha256(summary_path),
        "review_packet_sha256": sha256(review_path),
        "permanent_ingestion_isolated": True,
        "frozen_source_indexes_modified": False,
    }
    (args.output_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print("[progress] U5/U6 isolated permanent-ingestion evaluation finished", flush=True)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["automatic_safeguards_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
