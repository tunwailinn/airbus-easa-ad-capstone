#!/usr/bin/env python3
"""Offline evaluator for the locked five-PDF temporary-document QA run."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_DIR = ROOT / "data_processed/evaluations/unseen_5/temporary_primary"
DEFAULT_QUESTIONS = ROOT / "evaluation_sets/unseen_incoming_5_v1/unseen_questions.jsonl"
EVALUATOR_VERSION = "unseen-5-temporary-qa-eval-v1.0"


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
        "# Five-PDF Unseen Temporary QA Human Review Packet",
        "",
        f"Evaluator: `{EVALUATOR_VERSION}`",
        "",
        "This is a post-final unseen-document generalization probe. Private human-reviewed references are joined only after hosted inference.",
        "The frozen E5 primary final result remains separate and unchanged.",
        "",
        "## Automatic checks",
        "",
        f"- Questions: {summary['selected_question_count']}",
        f"- Hosted successes: {summary['success_count']}",
        f"- Hosted failures: {summary['failure_count']}",
        f"- Request success rate: {summary['request_success_rate']}",
        f"- Answerability/status accuracy: {summary['answerability_status_accuracy']}",
        f"- Temporary retrieval any-reference-page Recall@5: {summary['reference_page_any_recall_at_5']}",
        f"- Temporary retrieval full-reference-page coverage@5: {summary['reference_page_full_coverage_at_5']}",
        f"- Reference-page citation hit rate: {summary['reference_page_citation_hit_rate']}",
        f"- Target-AD citation hit rate: {summary['target_ad_citation_hit_rate']}",
        "",
        "## Human semantic rubric",
        "",
        "Review every successful response for answer correctness, material-condition completeness, compliance-time completeness, exception completeness, citation support and unsupported claims.",
        "",
    ]
    for row in rows:
        lines.extend([
            f"## {row['question_id']}",
            "",
            f"**AD:** `{row['target_ad_number']}`  ",
            f"**Stratum:** `{row['stratum']}`  ",
            f"**Category:** `{row['category']}`  ",
            f"**Answerable from AD:** `{row['answerable_from_ad']}`  ",
            f"**Reference page in top 5:** `{row['retrieval_reference_in_top5']}`  ",
            f"**All reference pages covered in top 5:** `{row['retrieval_all_reference_pages_covered_at_5']}`",
            "",
            "**Question**",
            "",
            str(row['question']),
            "",
            "**Human-reviewed reference answer**",
            "",
            str(row['reference_answer']),
            "",
            "**Human-reviewed source evidence**",
            "",
            json.dumps(row.get('source_evidence', []), ensure_ascii=False, indent=2),
            "",
            "**Hosted answer**",
            "",
            str(row.get('hosted_answer') or '[REQUEST FAILED]'),
            "",
            f"**Hosted status:** `{row.get('hosted_status')}`",
            "",
            f"**Hosted conditions:** {json.dumps(row.get('hosted_conditions', []), ensure_ascii=False)}",
            "",
            f"**Hosted compliance time:** {json.dumps(row.get('hosted_compliance_time', []), ensure_ascii=False)}",
            "",
            f"**Hosted exceptions:** {json.dumps(row.get('hosted_exceptions', []), ensure_ascii=False)}",
            "",
            f"**Reason for abstention:** {json.dumps(row.get('reason_for_abstention'), ensure_ascii=False)}",
            "",
            f"**Reference pages:** {row['reference_pages']}",
            "",
            f"**Citations:** {json.dumps(row.get('citations', []), ensure_ascii=False)}",
            "",
            "---",
            "",
        ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    paths = {
        "manifest": args.run_dir / "run_manifest.json",
        "summary": args.run_dir / "run_summary.json",
        "retrieval": args.run_dir / "retrieval_report.json",
        "responses": args.run_dir / "responses.jsonl",
        "failures": args.run_dir / "failures.jsonl",
    }
    for path in [*paths.values(), args.questions]:
        if not path.is_file():
            raise FileNotFoundError(path)

    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    if manifest.get("scope") != "five frozen unseen PDFs — temporary-document primary":
        raise ValueError("unseen evaluator accepts only the temporary-document primary run")
    if manifest.get("unseen_questions_sha256") != sha256(args.questions):
        raise ValueError("unseen question file hash differs from the hosted run")
    if manifest.get("permanent_ingestion") is not False:
        raise ValueError("temporary run manifest unexpectedly records permanent ingestion")

    questions = load_jsonl(args.questions)
    if len(questions) != 15:
        raise ValueError("expected 15 locked unseen questions")
    question_map = unique_map(questions, "question_id")
    retrieval_report = json.loads(paths["retrieval"].read_text(encoding="utf-8"))
    retrieval_map = unique_map(list(retrieval_report.get("questions", [])), "question_id")
    responses = load_jsonl(paths["responses"])
    failures = load_jsonl(paths["failures"])
    response_map = unique_map(responses, "question_id")
    failure_map = unique_map(failures, "question_id")
    if set(response_map) & set(failure_map):
        raise ValueError("question appears in both responses and failures")
    if set(response_map) | set(failure_map) != set(question_map):
        raise ValueError("temporary run output membership differs from locked unseen benchmark")

    status_correct = status_checks = 0
    ref_hits = ref_checks = 0
    target_hits = target_checks = 0
    rows: list[dict[str, Any]] = []

    for question in questions:
        qid = str(question["question_id"])
        retrieval = retrieval_map[qid]
        response = response_map.get(qid)
        failure = failure_map.get(qid)
        hosted = (response or {}).get("answer") or {}
        answerable = bool(question["answerable_from_ad"])
        hosted_status = hosted.get("status") if response else None
        status_ok = None
        if response is not None:
            status_ok = hosted_status == "answered" if answerable else hosted_status in {"insufficient_evidence", "conflicting_evidence"}
            status_checks += 1
            status_correct += int(bool(status_ok))

        citations = list(hosted.get("citations", []))
        reference_pages = [int(page) for page in question.get("reference_pages", [])]
        ref_hit = target_hit = None
        if response is not None and answerable:
            ref_checks += 1
            ref_hit = any(pages_overlap(citation, reference_pages) for citation in citations)
            ref_hits += int(bool(ref_hit))
            target_checks += 1
            target_hit = any(str(citation.get("ad_number")) == str(question["target_ad_number"]) for citation in citations)
            target_hits += int(bool(target_hit))

        retrieval_top5 = bool(retrieval.get("reference_page_any_at_5"))
        rows.append({
            "question_id": qid,
            "stratum": question["stratum"],
            "category": question["category"],
            "query_mode": question["query_mode"],
            "question": question["question"],
            "answerable_from_ad": answerable,
            "target_ad_number": question["target_ad_number"],
            "reference_pages": reference_pages,
            "reference_sections": question.get("reference_sections", []),
            "reference_answer": question.get("reference_answer", ""),
            "source_evidence": question.get("source_evidence", []),
            "retrieval_reference_page_rank": retrieval.get("reference_page_rank"),
            "retrieval_reference_in_top5": retrieval_top5,
            "retrieval_all_reference_pages_covered_at_5": bool(retrieval.get("reference_page_all_covered_at_5")),
            "request_failed": failure is not None,
            "failure": failure,
            "hosted_status": hosted_status,
            "answerability_status_correct": status_ok,
            "hosted_answer": hosted.get("answer"),
            "hosted_conditions": hosted.get("conditions", []),
            "hosted_compliance_time": hosted.get("compliance_time", []),
            "hosted_exceptions": hosted.get("exceptions", []),
            "reason_for_abstention": hosted.get("reason_for_abstention"),
            "citations": citations,
            "reference_page_citation_hit": ref_hit,
            "target_ad_citation_hit": target_hit,
            "attribution_hint": (
                "request_failure" if failure is not None
                else "temporary_retrieval_support_missing_from_top5" if answerable and not retrieval_top5
                else "generation_can_be_evaluated" if answerable
                else "abstention_can_be_evaluated"
            ),
        })

    summary = {
        "evaluator_version": EVALUATOR_VERSION,
        "selected_question_count": len(questions),
        "success_count": len(response_map),
        "failure_count": len(failure_map),
        "request_success_rate": ratio(len(response_map), len(questions)),
        "answerability_status_accuracy": ratio(status_correct, status_checks),
        "reference_page_any_recall_at_5": retrieval_report.get("reference_page_any_recall_at_5"),
        "reference_page_full_coverage_at_5": retrieval_report.get("reference_page_full_coverage_at_5"),
        "reference_page_citation_hit_rate": ratio(ref_hits, ref_checks),
        "target_ad_citation_hit_rate": ratio(target_hits, target_checks),
        "permanent_ingestion_started": False,
        "policy": "Post-final unseen generalization evaluation. Automatic checks require human semantic review and cannot change the frozen E5 final result.",
    }

    output_dir = args.output_dir or (args.run_dir / "evaluation")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"refusing to overwrite unseen temporary evaluation: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)
    report = {
        **summary,
        "unseen_questions_sha256": sha256(args.questions),
        "primary_run_summary_sha256": sha256(paths["summary"]),
        "retrieval_report_sha256": sha256(paths["retrieval"]),
        "responses_sha256": sha256(paths["responses"]),
        "rows": rows,
    }
    (output_dir / "automatic_evaluation.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    fields = [
        "question_id", "answer_correct", "material_conditions_complete", "compliance_time_complete",
        "exceptions_complete", "citation_support_correct", "unsupported_claims", "reviewer_notes",
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
