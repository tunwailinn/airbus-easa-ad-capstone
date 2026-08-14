#!/usr/bin/env python3
"""Offline evaluation for the E5 final oracle/reference-evidence diagnostic.

The strict primary final result remains authoritative. This evaluator compares the
oracle responses with the human-reviewed final references and the preserved primary
final responses, but it does not alter either run and cannot replace the primary
score. Semantic correctness remains a human-review dimension.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_ROOT = ROOT / "evaluation_sets/easa_airbus_ad_e5_benchmark_v1"
ORACLE_RUN_DIR = ROOT / "data_processed/evaluations/e5/layer_c/final/oracle/run"
PRIMARY_EVAL = ROOT / "data_processed/evaluations/e5/layer_c/final/primary/evaluation/automatic_evaluation.json"
DEFAULT_QUESTIONS = BENCHMARK_ROOT / "final_questions.jsonl"
EVALUATOR_VERSION = "e5-layer-c-final-oracle-eval-v1.0"


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
        "# E5 Final Oracle Diagnostic Review Packet",
        "",
        f"Evaluator: `{EVALUATOR_VERSION}`",
        "",
        "**Diagnostic only. The strict primary final score remains authoritative.**",
        "",
        "## Automatic oracle checks",
        "",
        f"- Questions: {summary['selected_question_count']}",
        f"- Oracle hosted successes: {summary['success_count']}",
        f"- Oracle hosted failures: {summary['failure_count']}",
        f"- Oracle answerability/status accuracy: {summary['answerability_status_accuracy']}",
        f"- Oracle reference-page citation hit rate: {summary['reference_page_citation_hit_rate']}",
        f"- Oracle target-AD citation hit rate: {summary['target_ad_citation_hit_rate']}",
        "",
        "Human review should compare the primary and oracle answers. If primary retrieval support was missing "
        "and oracle evidence resolves the answer, attribute the primary failure to Layer B. If primary support "
        "was present but the primary answer failed, compare whether cleaner oracle evidence resolves it before "
        "attributing the failure to Layer C generation versus evidence selection/completeness.",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {row['question_id']}",
                "",
                f"**Category:** `{row['category']}`  ",
                f"**Query mode:** `{row['query_mode']}`  ",
                f"**Primary reference passage in top 5:** `{row['primary_retrieval_reference_in_top5']}`",
                "",
                "**Question**",
                "",
                str(row["question"]),
                "",
                "**Human-reviewed reference answer**",
                "",
                str(row["reference_answer"]),
                "",
                "**Primary frozen answer**",
                "",
                str(row.get("primary_hosted_answer") or "[PRIMARY REQUEST FAILED]"),
                "",
                "**Oracle-evidence answer**",
                "",
                str(row.get("oracle_hosted_answer") or "[ORACLE REQUEST FAILED]"),
                "",
                f"**Primary status:** `{row.get('primary_hosted_status')}`  ",
                f"**Oracle status:** `{row.get('oracle_hosted_status')}`",
                "",
                f"**Oracle citations:** {json.dumps(row.get('oracle_citations', []), ensure_ascii=False)}",
                "",
                f"**Attribution hint:** {row['attribution_hint']}",
                "",
                "**Human oracle decision:** ☐ Oracle answer correct  ☐ Oracle answer incorrect",
                "",
                "**Reviewer attribution:** ☐ Layer B  ☐ Layer C  ☐ mixed/evidence-selection  ☐ benchmark ambiguity  ☐ not applicable",
                "",
                "**Reviewer notes:**",
                "",
                "---",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=ORACLE_RUN_DIR)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--primary-evaluation", type=Path, default=PRIMARY_EVAL)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    paths = {
        "manifest": args.run_dir / "run_manifest.json",
        "summary": args.run_dir / "run_summary.json",
        "responses": args.run_dir / "responses.jsonl",
        "failures": args.run_dir / "failures.jsonl",
    }
    for path in [*paths.values(), args.questions, args.primary_evaluation]:
        if not path.is_file():
            raise FileNotFoundError(path)

    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    if manifest.get("scope") != "E5 final oracle diagnostic":
        raise ValueError("oracle evaluator accepts only the E5 final oracle diagnostic run")
    if manifest.get("diagnostic_only") is not True:
        raise ValueError("final oracle run is not marked diagnostic_only")
    if manifest.get("final_questions_sha256") != sha256(args.questions):
        raise ValueError("oracle run final-question hash mismatch")

    questions = load_jsonl(args.questions)
    if len(questions) != 40:
        raise ValueError("expected 40 final questions")
    question_map = unique_map(questions, "question_id")

    primary = json.loads(args.primary_evaluation.read_text(encoding="utf-8"))
    if primary.get("final_questions_sha256") != sha256(args.questions):
        raise ValueError("primary evaluation final-question hash mismatch")
    primary_map = unique_map(list(primary.get("rows", [])), "question_id")
    if set(primary_map) != set(question_map):
        raise ValueError("primary evaluation question membership mismatch")

    responses = load_jsonl(paths["responses"])
    failures = load_jsonl(paths["failures"])
    response_map = unique_map(responses, "question_id")
    failure_map = unique_map(failures, "question_id")
    if set(response_map) & set(failure_map):
        raise ValueError("oracle question appears in both responses and failures")
    if set(response_map) | set(failure_map) != set(question_map):
        raise ValueError("oracle output membership differs from final benchmark")

    status_correct = status_checks = 0
    ref_hits = ref_checks = 0
    target_hits = target_checks = 0
    rows: list[dict[str, Any]] = []

    for question in questions:
        qid = str(question["question_id"])
        primary_row = primary_map[qid]
        response = response_map.get(qid)
        failure = failure_map.get(qid)
        hosted = (response or {}).get("answer") or {}
        status = hosted.get("status") if response is not None else None
        answerable = bool(question["answerable_from_ad"])
        status_ok = None
        if response is not None:
            status_ok = status == "answered" if answerable else status in {
                "insufficient_evidence",
                "conflicting_evidence",
            }
            status_checks += 1
            status_correct += int(bool(status_ok))

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

        primary_support = bool(primary_row.get("retrieval_reference_in_top5"))
        if failure is not None:
            hint = "oracle technical/provider request failure"
        elif not answerable:
            hint = "abstention negative-control comparison; evidence intentionally unchanged"
        elif not primary_support:
            hint = "primary reference evidence missing; if oracle answer is correct, primary failure is Layer B"
        else:
            hint = (
                "primary reference evidence was available; compare primary vs oracle to distinguish Layer C "
                "generation from top-5 evidence selection/completeness effects"
            )

        rows.append(
            {
                "question_id": qid,
                "category": question["category"],
                "query_mode": question["query_mode"],
                "question": question["question"],
                "answerable_from_ad": answerable,
                "target_ad_number": target_ad,
                "reference_pages": reference_pages,
                "reference_answer": question.get("reference_answer", ""),
                "primary_retrieval_reference_in_top5": primary_support,
                "primary_hosted_status": primary_row.get("hosted_status"),
                "primary_hosted_answer": primary_row.get("hosted_answer"),
                "oracle_request_failed": failure is not None,
                "oracle_failure": failure,
                "oracle_hosted_status": status,
                "oracle_answerability_status_correct": status_ok,
                "oracle_hosted_answer": hosted.get("answer"),
                "oracle_conditions": hosted.get("conditions", []),
                "oracle_compliance_time": hosted.get("compliance_time", []),
                "oracle_exceptions": hosted.get("exceptions", []),
                "oracle_reason_for_abstention": hosted.get("reason_for_abstention"),
                "oracle_citations": citations,
                "oracle_reference_page_citation_hit": ref_hit,
                "oracle_target_ad_citation_hit": target_hit,
                "attribution_hint": hint,
            }
        )

    summary = {
        "evaluator_version": EVALUATOR_VERSION,
        "diagnostic_only": True,
        "selected_question_count": len(questions),
        "success_count": len(response_map),
        "failure_count": len(failure_map),
        "request_success_rate": ratio(len(response_map), len(questions)),
        "answerability_status_accuracy": ratio(status_correct, status_checks),
        "reference_page_citation_hit_rate": ratio(ref_hits, ref_checks),
        "target_ad_citation_hit_rate": ratio(target_hits, target_checks),
        "strict_primary_result_remains_authoritative": True,
        "policy": (
            "Post-hoc final oracle diagnostic only. Automatic oracle checks do not determine semantic "
            "correctness and cannot replace or adjust the strict primary final score."
        ),
    }

    output_dir = args.output_dir or (args.run_dir / "evaluation")
    output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        **summary,
        "final_questions_sha256": sha256(args.questions),
        "oracle_run_summary_sha256": sha256(paths["summary"]),
        "oracle_responses_sha256": sha256(paths["responses"]),
        "primary_evaluation_sha256": sha256(args.primary_evaluation),
        "rows": rows,
    }
    (output_dir / "automatic_evaluation.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    fields = [
        "question_id",
        "oracle_answer_correct",
        "oracle_material_conditions_complete",
        "oracle_compliance_time_complete",
        "oracle_exceptions_complete",
        "oracle_citation_support_correct",
        "oracle_unsupported_claims",
        "primary_vs_oracle_attribution",
        "reviewer_notes",
    ]
    with (output_dir / "human_review.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({"question_id": row["question_id"]})

    (output_dir / "review_packet.md").write_text(
        render_packet(rows, summary), encoding="utf-8"
    )
    print(json.dumps({**summary, "output_dir": str(output_dir)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
