#!/usr/bin/env python3
"""Evaluate a Layer C development run against private human-reviewed references.

This evaluator is offline-only: benchmark labels/reference answers are never sent
to the hosted model. It produces deterministic technical metrics plus a human
review packet for semantic correctness and error attribution.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QUESTIONS = ROOT / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1/development_questions.jsonl"
DEFAULT_RETRIEVAL_REPORT = ROOT / "data_processed/evaluations/e5/e5d_development_evaluation.json"
EVALUATOR_VERSION = "e5-layer-c-development-eval-v1.0"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def map_unique(rows: list[dict[str, Any]], key: str, label: str) -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = str(row[key])
        if value in mapped:
            raise ValueError(f"duplicate {label} {key}: {value}")
        mapped[value] = row
    return mapped


def pages_overlap(citation: dict[str, Any], reference_pages: list[int]) -> bool:
    start = int(citation.get("page_start") or 0)
    end = int(citation.get("page_end") or start)
    return any(start <= int(page) <= end for page in reference_pages)


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def render_review_packet(rows: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    lines = [
        "# Layer C Development Human Review Packet",
        "",
        f"Evaluator: `{EVALUATOR_VERSION}`",
        "",
        "This file is generated **after** hosted inference. Private reference fields below were not part of the model prompt.",
        "",
        "## Automatic checks",
        "",
        f"- Selected questions: {summary['selected_question_count']}",
        f"- Hosted successes: {summary['success_count']}",
        f"- Hosted failures: {summary['failure_count']}",
        f"- Answerability/status accuracy: {summary['answerability_status_accuracy']}",
        f"- Reference-page citation hit rate: {summary['reference_page_citation_hit_rate']}",
        f"- Target-AD citation hit rate: {summary['target_ad_citation_hit_rate']}",
        "",
        "## Human semantic rubric",
        "",
        "For each successful answer, review these fields in `human_review.csv`: `answer_correct`, `material_conditions_complete`, `compliance_time_complete`, `exceptions_complete`, `citation_support_correct`, and `unsupported_claims`. Use `1`/`0`; use `na` only when a dimension is genuinely not applicable.",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {row['question_id']}",
                "",
                f"**Category:** `{row['category']}`  ",
                f"**Query mode:** `{row['query_mode']}`  ",
                f"**Retrieval support in frozen top 5:** `{row['retrieval_reference_in_top5']}`",
                "",
                "**Question**",
                "",
                str(row["question"]),
                "",
                "**Human-reviewed reference answer**",
                "",
                str(row["reference_answer"]),
                "",
                "**Hosted answer**",
                "",
                str(row.get("hosted_answer") or "[REQUEST FAILED]"),
                "",
                f"**Hosted status:** `{row.get('hosted_status')}`",
                "",
                f"**Hosted conditions:** {json.dumps(row.get('hosted_conditions', []), ensure_ascii=False)}",
                "",
                f"**Hosted compliance time:** {json.dumps(row.get('hosted_compliance_time', []), ensure_ascii=False)}",
                "",
                f"**Hosted exceptions:** {json.dumps(row.get('hosted_exceptions', []), ensure_ascii=False)}",
                "",
                f"**Reference pages:** {row['reference_pages']}",
                "",
                f"**Citations:** {json.dumps(row.get('citations', []), ensure_ascii=False)}",
                "",
                "---",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--retrieval-report", type=Path, default=DEFAULT_RETRIEVAL_REPORT)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir
    manifest_path = run_dir / "run_manifest.json"
    responses_path = run_dir / "responses.jsonl"
    failures_path = run_dir / "failures.jsonl"
    for path in (manifest_path, responses_path, failures_path, args.questions, args.retrieval_report):
        if not path.exists():
            raise FileNotFoundError(path)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("scope") != "E5 development only":
        raise ValueError("Layer C evaluator accepts E5 development runs only")

    questions = load_jsonl(args.questions)
    question_map = map_unique(questions, "question_id", "question")
    retrieval_report = json.loads(args.retrieval_report.read_text(encoding="utf-8"))
    if retrieval_report.get("benchmark_sha256") != sha256(args.questions):
        raise ValueError("retrieval report benchmark SHA does not match development questions")
    retrieval_map = map_unique(list(retrieval_report.get("questions", [])), "question_id", "retrieval row")

    responses = load_jsonl(responses_path)
    failures = load_jsonl(failures_path)
    response_map = map_unique(responses, "question_id", "response")
    failure_map = map_unique(failures, "question_id", "failure")
    overlap = set(response_map) & set(failure_map)
    if overlap:
        raise ValueError(f"question appears in both responses and failures: {sorted(overlap)}")

    selected_ids = list(response_map) + list(failure_map)
    if len(selected_ids) != int(manifest.get("selected_question_count", -1)):
        raise ValueError("run outputs do not match selected_question_count in manifest")
    unknown = set(selected_ids) - set(question_map)
    if unknown:
        raise ValueError(f"run contains unknown development questions: {sorted(unknown)}")

    rows: list[dict[str, Any]] = []
    status_correct_count = 0
    status_checked_count = 0
    ref_page_hits = 0
    ref_page_checks = 0
    target_ad_hits = 0
    target_ad_checks = 0
    retrieval_top5_count = 0
    retrieval_answerable_count = 0

    for qid in selected_ids:
        question = question_map[qid]
        retrieval = retrieval_map.get(qid)
        if retrieval is None:
            raise ValueError(f"missing frozen E5-D retrieval row for {qid}")
        answerable = bool(question["answerable_from_ad"])
        rank = retrieval.get("rank_at_20")
        retrieval_top5 = bool(answerable and rank is not None and int(rank) <= 5)
        if answerable:
            retrieval_answerable_count += 1
            retrieval_top5_count += int(retrieval_top5)

        response_row = response_map.get(qid)
        failure_row = failure_map.get(qid)
        hosted_answer: dict[str, Any] | None = None
        if response_row is not None:
            hosted_answer = response_row.get("answer") or {}
            status = str(hosted_answer.get("status"))
            expected_answered = answerable
            status_correct = (status == "answered") if expected_answered else (status in {"insufficient_evidence", "conflicting_evidence"})
            status_checked_count += 1
            status_correct_count += int(status_correct)
        else:
            status = None
            status_correct = None

        citations = list((hosted_answer or {}).get("citations", []))
        reference_pages = [int(page) for page in question.get("reference_pages", [])]
        target_ad = question.get("target_ad_number")
        ref_page_hit = None
        target_ad_hit = None
        if response_row is not None and answerable and reference_pages:
            ref_page_checks += 1
            ref_page_hit = any(pages_overlap(citation, reference_pages) for citation in citations)
            ref_page_hits += int(ref_page_hit)
        if response_row is not None and answerable and target_ad:
            target_ad_checks += 1
            target_ad_hit = any(str(citation.get("ad_number")) == str(target_ad) for citation in citations)
            target_ad_hits += int(target_ad_hit)

        attribution_hint = "request_failure" if failure_row is not None else None
        if failure_row is None:
            if answerable and not retrieval_top5:
                attribution_hint = "retrieval_support_missing_from_top5"
            elif answerable:
                attribution_hint = "generation_can_be_evaluated"
            else:
                attribution_hint = "abstention_can_be_evaluated"

        rows.append(
            {
                "question_id": qid,
                "category": question["category"],
                "query_mode": question["query_mode"],
                "question": question["question"],
                "answerable_from_ad": answerable,
                "target_ad_number": target_ad,
                "reference_pages": reference_pages,
                "reference_sections": question.get("reference_sections", []),
                "reference_answer": question.get("reference_answer", ""),
                "required_conditions": question.get("required_conditions", []),
                "required_exceptions": question.get("required_exceptions", []),
                "retrieval_rank": rank,
                "retrieval_reference_in_top5": retrieval_top5,
                "request_failed": failure_row is not None,
                "failure": failure_row,
                "hosted_status": status,
                "answerability_status_correct": status_correct,
                "hosted_answer": (hosted_answer or {}).get("answer"),
                "hosted_conditions": (hosted_answer or {}).get("conditions", []),
                "hosted_compliance_time": (hosted_answer or {}).get("compliance_time", []),
                "hosted_exceptions": (hosted_answer or {}).get("exceptions", []),
                "reason_for_abstention": (hosted_answer or {}).get("reason_for_abstention"),
                "citations": citations,
                "reference_page_citation_hit": ref_page_hit,
                "target_ad_citation_hit": target_ad_hit,
                "attribution_hint": attribution_hint,
            }
        )

    summary = {
        "evaluator_version": EVALUATOR_VERSION,
        "run_id": manifest.get("run_id"),
        "provider": manifest.get("provider"),
        "model": manifest.get("model"),
        "reasoning_effort": manifest.get("reasoning_effort"),
        "selected_question_count": len(selected_ids),
        "success_count": len(response_map),
        "failure_count": len(failure_map),
        "request_success_rate": ratio(len(response_map), len(selected_ids)),
        "answerability_status_accuracy": ratio(status_correct_count, status_checked_count),
        "reference_page_citation_hit_rate": ratio(ref_page_hits, ref_page_checks),
        "target_ad_citation_hit_rate": ratio(target_ad_hits, target_ad_checks),
        "frozen_retrieval_reference_in_top5_rate_for_answerable_selected": ratio(
            retrieval_top5_count, retrieval_answerable_count
        ),
        "policy": (
            "Automatic checks cover transport, answerability/abstention status, citation targeting, and frozen retrieval support. "
            "Semantic answer correctness and material-condition completeness require human review; reference labels are used only offline after inference."
        ),
    }

    output_dir = args.output_dir or (run_dir / "evaluation")
    output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        **summary,
        "questions_sha256": sha256(args.questions),
        "retrieval_report_sha256": sha256(args.retrieval_report),
        "responses_sha256": sha256(responses_path),
        "rows": rows,
    }
    (output_dir / "automatic_evaluation.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    review_fields = [
        "question_id",
        "answer_correct",
        "material_conditions_complete",
        "compliance_time_complete",
        "exceptions_complete",
        "citation_support_correct",
        "unsupported_claims",
        "reviewer_notes",
    ]
    with (output_dir / "human_review.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=review_fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({"question_id": row["question_id"]})

    (output_dir / "review_packet.md").write_text(
        render_review_packet(rows, summary), encoding="utf-8"
    )

    print(json.dumps({**summary, "output_dir": str(output_dir)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
