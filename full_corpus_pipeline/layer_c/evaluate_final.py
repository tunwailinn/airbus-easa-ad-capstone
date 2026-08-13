#!/usr/bin/env python3
"""Offline evaluation for the one-time E5 Layer C final benchmark.

This command runs only after final hosted inference has completed. It joins the
private human-reviewed final references to the preserved primary run and produces
deterministic technical metrics plus a human semantic-review packet. It never
changes retrieval, evidence, prompt, model, or the primary final outputs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_DIR = ROOT / "data_processed/evaluations/e5/layer_c/final/primary"
DEFAULT_QUESTIONS = ROOT / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1/final_questions.jsonl"
EVALUATOR_VERSION = "e5-layer-c-final-eval-v1.0"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def unique_map(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = str(row[key])
        if value in output:
            raise ValueError(f"duplicate {key}: {value}")
        output[value] = row
    return output


def pages_overlap(citation: dict[str, Any], reference_pages: list[int]) -> bool:
    start = int(citation.get("page_start") or 0)
    end = int(citation.get("page_end") or start)
    return any(start <= int(page) <= end for page in reference_pages)


def ratio(num: int, den: int) -> float | None:
    return num / den if den else None


def render_packet(rows: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    lines = [
        "# E5 Layer C Final Human Review Packet",
        "",
        f"Evaluator: `{EVALUATOR_VERSION}`",
        "",
        "Private reference fields below are joined only after the one-time hosted final run.",
        "The strict frozen final benchmark remains the primary result; any later ambiguity/error analysis is post-hoc only.",
        "",
        "## Automatic checks",
        "",
        f"- Final questions: {summary['selected_question_count']}",
        f"- Hosted successes: {summary['success_count']}",
        f"- Hosted failures: {summary['failure_count']}",
        f"- Request success rate: {summary['request_success_rate']}",
        f"- Answerability/status accuracy: {summary['answerability_status_accuracy']}",
        f"- Reference-page citation hit rate: {summary['reference_page_citation_hit_rate']}",
        f"- Target-AD citation hit rate: {summary['target_ad_citation_hit_rate']}",
        "",
        "## Human semantic rubric",
        "",
        "Score each successful answer in `human_review.csv`: answer correctness, material-condition completeness, compliance-time completeness, exception completeness, citation support, and unsupported claims.",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {row['question_id']}",
                "",
                f"**Category:** `{row['category']}`  ",
                f"**Query mode:** `{row['query_mode']}`  ",
                f"**Frozen E5-D reference passage in top 5:** `{row['retrieval_reference_in_top5']}`",
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
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir
    paths = {
        "manifest": run_dir / "run_manifest.json",
        "summary": run_dir / "run_summary.json",
        "retrieval": run_dir / "retrieval_report.json",
        "responses": run_dir / "responses.jsonl",
        "failures": run_dir / "failures.jsonl",
    }
    for path in [*paths.values(), args.questions]:
        if not path.is_file():
            raise FileNotFoundError(path)

    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    if manifest.get("scope") != "E5 one-time final benchmark":
        raise ValueError("final evaluator accepts only the primary E5 final run")
    if manifest.get("final_questions_sha256") != sha256(args.questions):
        raise ValueError("final question file hash differs from the primary run")

    questions = load_jsonl(args.questions)
    if len(questions) != 40:
        raise ValueError("expected 40 final questions")
    question_map = unique_map(questions, "question_id")
    retrieval_report = json.loads(paths["retrieval"].read_text(encoding="utf-8"))
    if retrieval_report.get("benchmark_sha256") != sha256(args.questions):
        raise ValueError("final retrieval report benchmark hash mismatch")
    retrieval_map = unique_map(list(retrieval_report.get("questions", [])), "question_id")

    responses = load_jsonl(paths["responses"])
    failures = load_jsonl(paths["failures"])
    response_map = unique_map(responses, "question_id")
    failure_map = unique_map(failures, "question_id")
    if set(response_map) & set(failure_map):
        raise ValueError("final question appears in both responses and failures")
    if set(response_map) | set(failure_map) != set(question_map):
        raise ValueError("final run output membership differs from final benchmark")

    status_correct = status_checks = 0
    ref_hits = ref_checks = 0
    target_hits = target_checks = 0
    rows: list[dict[str, Any]] = []

    for question in questions:
        qid = str(question["question_id"])
        retrieval = retrieval_map[qid]
        answerable = bool(question["answerable_from_ad"])
        rank = retrieval.get("rank_at_20")
        retrieval_top5 = bool(answerable and rank is not None and int(rank) <= 5)
        response = response_map.get(qid)
        failure = failure_map.get(qid)
        hosted = (response or {}).get("answer") or {}
        hosted_status = hosted.get("status") if response is not None else None
        current_status_correct = None
        if response is not None:
            current_status_correct = (
                hosted_status == "answered"
                if answerable
                else hosted_status in {"insufficient_evidence", "conflicting_evidence"}
            )
            status_checks += 1
            status_correct += int(bool(current_status_correct))

        citations = list(hosted.get("citations", []))
        reference_pages = [int(page) for page in question.get("reference_pages", [])]
        target_ad = question.get("target_ad_number")
        ref_hit = target_hit = None
        if response is not None and answerable and reference_pages:
            ref_checks += 1
            ref_hit = any(pages_overlap(citation, reference_pages) for citation in citations)
            ref_hits += int(bool(ref_hit))
        if response is not None and answerable and target_ad:
            target_checks += 1
            target_hit = any(str(citation.get("ad_number")) == str(target_ad) for citation in citations)
            target_hits += int(bool(target_hit))

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
                "request_failed": failure is not None,
                "failure": failure,
                "hosted_status": hosted_status,
                "answerability_status_correct": current_status_correct,
                "hosted_answer": hosted.get("answer"),
                "hosted_conditions": hosted.get("conditions", []),
                "hosted_compliance_time": hosted.get("compliance_time", []),
                "hosted_exceptions": hosted.get("exceptions", []),
                "reason_for_abstention": hosted.get("reason_for_abstention"),
                "citations": citations,
                "reference_page_citation_hit": ref_hit,
                "target_ad_citation_hit": target_hit,
                "attribution_hint": (
                    "request_failure"
                    if failure is not None
                    else "retrieval_support_missing_from_top5"
                    if answerable and not retrieval_top5
                    else "generation_can_be_evaluated"
                    if answerable
                    else "abstention_can_be_evaluated"
                ),
            }
        )

    summary = {
        "evaluator_version": EVALUATOR_VERSION,
        "selected_question_count": len(questions),
        "success_count": len(response_map),
        "failure_count": len(failure_map),
        "request_success_rate": ratio(len(response_map), len(questions)),
        "answerability_status_accuracy": ratio(status_correct, status_checks),
        "reference_page_citation_hit_rate": ratio(ref_hits, ref_checks),
        "target_ad_citation_hit_rate": ratio(target_hits, target_checks),
        "retrieval_overall": retrieval_report.get("overall"),
        "retrieval_by_query_mode": retrieval_report.get("by_query_mode"),
        "policy": (
            "Strict frozen final-test evaluation. Automatic checks do not replace human semantic review. "
            "No post-test tuning or post-hoc ambiguity adjustment may replace the primary final result."
        ),
    }

    output_dir = args.output_dir or (run_dir / "evaluation")
    output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        **summary,
        "final_questions_sha256": sha256(args.questions),
        "primary_run_summary_sha256": sha256(paths["summary"]),
        "retrieval_report_sha256": sha256(paths["retrieval"]),
        "responses_sha256": sha256(paths["responses"]),
        "rows": rows,
    }
    (output_dir / "automatic_evaluation.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    fields = [
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
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({"question_id": row["question_id"]})

    (output_dir / "review_packet.md").write_text(render_packet(rows, summary), encoding="utf-8")
    print(json.dumps({**summary, "output_dir": str(output_dir)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
