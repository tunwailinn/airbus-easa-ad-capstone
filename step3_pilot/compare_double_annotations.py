#!/usr/bin/env python3
"""Compare the ten independent Step 3 annotation pairs.

The report is deliberately an adjudication aid, not an automatic merge.  It
compares the semantic annotation sections, reports evidence-page/quote overlap,
and creates one decision template per logical publication.  Annotator A and B
files remain unchanged.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any


SEMANTIC_SECTIONS = (
    "ad_identity",
    "publication",
    "applicability_groups",
    "definitions",
    "unsafe_condition",
    "requirements",
    "exceptions",
    "previous_action_credit",
    "referenced_publications",
    "relationships",
    "amoc_and_contacts",
    "classification",
)

# These identifiers are local bookkeeping. Two independent annotators may use
# different numbering without disagreeing about the source document.
LOCAL_ID_KEYS = {
    "group_id",
    "definition_id",
    "requirement_id",
    "parent_requirement_id",
    "follow_on_requirement_ids",
    "terminates_requirement_ids",
    "method_publication_ids",
    "applies_to_requirement_ids",
    "publication_id",
    "credited_publication_ids",
    "relationship_id",
    "contact_id",
    "evidence_ids",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--selection",
        type=Path,
        default=Path("step3_pilot/selection/pilot_selection.json"),
    )
    parser.add_argument(
        "--annotator-a",
        type=Path,
        default=Path("step3_pilot/submitted/annotator_a"),
    )
    parser.add_argument(
        "--annotator-b",
        type=Path,
        default=Path("step3_pilot/submitted/annotator_b"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("step3_pilot/adjudication"),
    )
    parser.add_argument(
        "--roster",
        type=Path,
        default=Path("step3_pilot/selection/annotation_assignment_roster.csv"),
    )
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="exit 1 unless all ten A/B pairs are present and comparable",
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def canonicalize(value: Any) -> Any:
    """Remove local IDs and normalize whitespace without hiding content."""

    if isinstance(value, dict):
        return {
            key: canonicalize(item)
            for key, item in sorted(value.items())
            if key not in LOCAL_ID_KEYS
        }
    if isinstance(value, list):
        return [canonicalize(item) for item in value]
    if isinstance(value, str):
        return normalize_text(value)
    return value


def escape_pointer(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def diff_values(a: Any, b: Any, path: str = "") -> list[dict[str, Any]]:
    if type(a) is not type(b):
        return [{"field_path": path or "/", "annotator_a": a, "annotator_b": b}]
    if isinstance(a, dict):
        differences: list[dict[str, Any]] = []
        for key in sorted(set(a) | set(b)):
            child = f"{path}/{escape_pointer(key)}"
            if key not in a:
                differences.append(
                    {"field_path": child, "annotator_a": {"missing": True}, "annotator_b": b[key]}
                )
            elif key not in b:
                differences.append(
                    {"field_path": child, "annotator_a": a[key], "annotator_b": {"missing": True}}
                )
            else:
                differences.extend(diff_values(a[key], b[key], child))
        return differences
    if isinstance(a, list):
        differences = []
        for index in range(max(len(a), len(b))):
            child = f"{path}/{index}"
            if index >= len(a):
                differences.append(
                    {"field_path": child, "annotator_a": {"missing": True}, "annotator_b": b[index]}
                )
            elif index >= len(b):
                differences.append(
                    {"field_path": child, "annotator_a": a[index], "annotator_b": {"missing": True}}
                )
            else:
                differences.extend(diff_values(a[index], b[index], child))
        return differences
    if a != b:
        return [{"field_path": path or "/", "annotator_a": a, "annotator_b": b}]
    return []


def annotation_index(directory: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    result: dict[str, tuple[Path, dict[str, Any]]] = {}
    if not directory.exists():
        return result
    for path in sorted(directory.glob("*.annotation.json")):
        record = load_json(path)
        file_id = (record.get("source_document") or {}).get("file_instance_id")
        if not file_id:
            raise ValueError(f"{path}: missing source_document.file_instance_id")
        if file_id in result:
            raise ValueError(f"{directory}: duplicate file_instance_id {file_id}")
        result[file_id] = (path, record)
    return result


def semantic_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        section: canonicalize(deepcopy(record.get(section)))
        for section in SEMANTIC_SECTIONS
    }


def evidence_signature(span: dict[str, Any]) -> str:
    payload = {
        "page_number": span.get("page_number"),
        "section": span.get("section"),
        "exact_quote": normalize_text(span.get("exact_quote") or ""),
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    return len(left & right) / len(left | right)


def stable_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    args = parse_args()
    selection = load_json(args.selection)
    if not isinstance(selection, list):
        raise ValueError("pilot selection must be a JSON array")
    double_rows = [row for row in selection if bool(row.get("double_annotation"))]
    if len(double_rows) != 10:
        raise ValueError(f"expected exactly 10 double-annotation rows, found {len(double_rows)}")
    with args.roster.open("r", encoding="utf-8", newline="") as handle:
        roster_rows = list(csv.DictReader(handle))
    roster = {row["ad_number"]: row for row in roster_rows}
    if len(roster) != 30:
        raise ValueError(f"expected 30 unique assignment rows, found {len(roster)}")

    index_a = annotation_index(args.annotator_a)
    index_b = annotation_index(args.annotator_b)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    decisions_dir = args.output_dir / "decision_templates"
    decisions_dir.mkdir(parents=True, exist_ok=True)

    comparisons: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    complete_pairs = 0
    total_differences = 0
    section_matches = 0
    section_total = 0
    evidence_scores: list[float] = []

    for row in double_rows:
        file_id = row["file_instance_id"]
        assignment = roster[row["ad_number"]]
        a_item = index_a.get(file_id)
        b_item = index_b.get(file_id)
        base = {
            "ad_number": row["ad_number"],
            "logical_version_key": row["logical_version_key"],
            "file_instance_id": file_id,
            "annotator_a_expected": assignment["annotator_a"],
            "annotator_b_expected": assignment["annotator_b"],
            "adjudicator_expected": assignment["machine_adjudicator"],
        }
        if not a_item or not b_item:
            missing = []
            if not a_item:
                missing.append("annotator_a")
            if not b_item:
                missing.append("annotator_b")
            comparison = {**base, "status": "pending", "missing": missing}
            comparisons.append(comparison)
            summary_rows.append(
                {
                    "ad_number": row["ad_number"],
                    "file_instance_id": file_id,
                    "status": "pending",
                    "difference_count": "",
                    "section_agreement": "",
                    "evidence_jaccard": "",
                }
            )
            continue

        a_path, a_record = a_item
        b_path, b_record = b_item
        for label, record in (("A", a_record), ("B", b_record)):
            identity = record.get("ad_identity") or {}
            source = record.get("source_document") or {}
            if identity.get("ad_number") != row["ad_number"]:
                raise ValueError(f"{label} {row['ad_number']}: AD number does not match selection")
            if identity.get("logical_version_key") != row["logical_version_key"]:
                raise ValueError(f"{label} {row['ad_number']}: logical version does not match selection")
            if source.get("file_sha256") != row["file_sha256"]:
                raise ValueError(f"{label} {row['ad_number']}: source hash does not match selection")
            expected_annotator = (
                assignment["annotator_a"] if label == "A" else assignment["annotator_b"]
            )
            actual_annotators = {
                item.get("annotator_id")
                for item in (record.get("annotation_metadata") or {}).get("annotators", [])
            }
            if expected_annotator not in actual_annotators:
                raise ValueError(
                    f"{label} {row['ad_number']}: expected annotator "
                    f"{expected_annotator!r}, found {sorted(actual_annotators)}"
                )

        semantic_a = semantic_record(a_record)
        semantic_b = semantic_record(b_record)
        differences = diff_values(semantic_a, semantic_b)
        section_agreement = {
            section: semantic_a[section] == semantic_b[section]
            for section in SEMANTIC_SECTIONS
        }
        evidence_a = {
            evidence_signature(item) for item in a_record.get("evidence_spans", [])
        }
        evidence_b = {
            evidence_signature(item) for item in b_record.get("evidence_spans", [])
        }
        evidence_overlap = jaccard(evidence_a, evidence_b)
        comparison = {
            **base,
            "status": "ready_for_adjudication",
            "annotator_a_file": str(a_path),
            "annotator_b_file": str(b_path),
            "annotator_a_semantic_sha256": stable_sha256(semantic_a),
            "annotator_b_semantic_sha256": stable_sha256(semantic_b),
            "difference_count": len(differences),
            "section_agreement": section_agreement,
            "evidence": {
                "annotator_a_span_count": len(evidence_a),
                "annotator_b_span_count": len(evidence_b),
                "exact_signature_jaccard": round(evidence_overlap, 6),
                "shared_span_count": len(evidence_a & evidence_b),
            },
            "differences": differences,
        }
        comparisons.append(comparison)
        matched = sum(section_agreement.values())
        complete_pairs += 1
        total_differences += len(differences)
        section_matches += matched
        section_total += len(SEMANTIC_SECTIONS)
        evidence_scores.append(evidence_overlap)
        summary_rows.append(
            {
                "ad_number": row["ad_number"],
                "file_instance_id": file_id,
                "status": "ready_for_adjudication",
                "difference_count": len(differences),
                "section_agreement": f"{matched}/{len(SEMANTIC_SECTIONS)}",
                "evidence_jaccard": f"{evidence_overlap:.6f}",
            }
        )
        decision = {
            "ad_number": row["ad_number"],
            "logical_version_key": row["logical_version_key"],
            "file_instance_id": file_id,
            "annotator_a_file": str(a_path),
            "annotator_b_file": str(b_path),
            "adjudicator_id": assignment["machine_adjudicator"],
            "comparison_sha256": stable_sha256(comparison),
            "decision_status": "pending",
            "resolved_record_file": None,
            "decisions": [
                {
                    "field_path": item["field_path"],
                    "resolution": "pending",
                    "accepted_value_from": None,
                    "resolved_value": None,
                    "source_page_numbers": [],
                    "rationale": None,
                }
                for item in differences
            ],
            "overall_rationale": None,
        }
        dump_json(
            decisions_dir / f"{row['ad_number']}__{file_id}.adjudication.json",
            decision,
        )

    report = {
        "selection_file": str(args.selection),
        "expected_pair_count": 10,
        "complete_pair_count": complete_pairs,
        "pending_pair_count": 10 - complete_pairs,
        "total_semantic_difference_count": total_differences,
        "section_exact_agreement": (
            round(section_matches / section_total, 6) if section_total else None
        ),
        "mean_evidence_exact_signature_jaccard": (
            round(sum(evidence_scores) / len(evidence_scores), 6)
            if evidence_scores
            else None
        ),
        "comparisons": comparisons,
    }
    dump_json(args.output_dir / "double_annotation_comparison.json", report)
    with (args.output_dir / "double_annotation_summary.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0]))
        writer.writeheader()
        writer.writerows(summary_rows)

    print(
        f"Compared {complete_pairs}/10 pairs; "
        f"pending={10 - complete_pairs}; semantic differences={total_differences}"
    )
    if args.require_complete and complete_pairs != 10:
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
