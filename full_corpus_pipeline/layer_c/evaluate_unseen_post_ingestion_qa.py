#!/usr/bin/env python3
"""Offline U7 evaluator for post-ingestion E5-D + frozen Layer C unseen QA."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_DIR = ROOT / "data_processed/evaluations/unseen_5/post_ingestion_primary"
DEFAULT_QUESTIONS = ROOT / "evaluation_sets/unseen_incoming_5_v1/unseen_questions.jsonl"
DEFAULT_TEMP_RETRIEVAL = ROOT / "data_processed/evaluations/unseen_5/temporary_primary/retrieval_report.json"
EVALUATOR_VERSION = "unseen-5-post-ingestion-qa-eval-v1.0"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


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


def norm(value: str) -> str:
    value = value.replace("\u00ad", "")
    value = re.sub(r"-\s*\n\s*", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip().casefold()


def quote_containment(
    question: dict[str, Any], evidence: list[dict[str, Any]]
) -> tuple[bool, bool, list[dict[str, Any]]]:
    normalized_evidence = [norm(str(item.get("text", ""))) for item in evidence]
    results: list[dict[str, Any]] = []
    for source in question.get("source_evidence", []):
        quote = str(source.get("quote", ""))
        normalized_quote = norm(quote)
        supporting = [
            str(item.get("evidence_id"))
            for item, text in zip(evidence, normalized_evidence)
            if normalized_quote and normalized_quote in text
        ]
        results.append(
            {
                "page": int(source.get("page", 0)),
                "section": source.get("section"),
                "quote_contained": bool(supporting),
                "supporting_evidence_ids": supporting,
            }
        )
    any_hit = any(item["quote_contained"] for item in results) if results else False
    all_hit = all(item["quote_contained"] for item in results) if results else False
    return any_hit, all_hit, results


def render_packet(rows: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    lines = [
        "# Five-PDF Unseen Post-Ingestion QA Human Review Packet",
        "",
        f"Evaluator: `{EVALUATOR_VERSION}`",
        "",
        "This is U7: the same 15 locked unseen questions evaluated after the five PDFs were admitted to an isolated post-ingestion E5-compatible derivative.",
        "Private target/reference fields are joined only after hosted inference. The frozen 40-question E5 final result and the locked U3/U4 temporary result remain separate.",
        "",
        "## Automatic checks",
        "",
        f"- Questions: **{summary['selected_question_count']}**",
        f"- Hosted successes: **{summary['success_count']}**",
        f"- Hosted failures: **{summary['failure_count']}**",
        f"- Request success rate: **{summary['request_success_rate']}**",
        f"- Answerability/status accuracy: **{summary['answerability_status_accuracy']}**",
        f"- Post-ingestion reference-page any Recall@5: **{summary['reference_page_any_recall_at_5']}**",
        f"- Post-ingestion full-reference-page coverage@5: **{summary['reference_page_full_coverage_at_5']}**",
        f"- Any approved reference quote contained@5: **{summary['any_reference_quote_containment_at_5']}**",
        f"- All approved reference quotes contained@5: **{summary['all_reference_quotes_containment_at_5']}**",
        f"- Reference-page citation hit rate: **{summary['reference_page_citation_hit_rate']}**",
        f"- Target-AD citation hit rate: **{summary['target_ad_citation_hit_rate']}**",
        "",
        "## Human semantic rubric",
        "",
        "Review every successful response for answer correctness, requested-scope completeness, material conditions, compliance-time completeness, exceptions, citation support, and unsupported claims. Do not require facts the question did not ask for.",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {row['question_id']}",
                "",
                f"**AD:** `{row['target_ad_number']}`  ",
                f"**Stratum:** `{row['stratum']}`  ",
                f"**Category:** `{row['category']}`  ",
                f"**Post-ingestion route:** `{row['post_ingestion_route_mode']}`  ",
                f"**Answerable from AD:** `{row['answerable_from_ad']}`  ",
                f"**Reference page in top 5:** `{row['retrieval_reference_in_top5']}`  ",
                f"**All reference pages covered in top 5:** `{row['retrieval_all_reference_pages_covered_at_5']}`  ",
                f"**Any approved quote contained in top 5:** `{row['any_reference_quote_contained_in_top5']}`  ",
                f"**All approved quotes contained in top 5:** `{row['all_reference_quotes_contained_in_top5']}`",
                "",
                "**Question**",
                "",
                str(row["question"]),
                "",
                "**Human-reviewed reference answer**",
                "",
                str(row["reference_answer"]),
                "",
                "**Human-reviewed source evidence**",
                "",
                json.dumps(row.get("source_evidence", []), ensure_ascii=False, indent=2),
                "",
                "**Post-ingestion reranked top-5 prompt evidence**",
                "",
                json.dumps(row.get("prompt_evidence", []), ensure_ascii=False, indent=2),
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
                f"**Reason for abstention:** {json.dumps(row.get('reason_for_abstention'), ensure_ascii=False)}",
                "",
                f"**Reference pages:** {row['reference_pages']}",
                "",
                f"**Citations:** {json.dumps(row.get('citations', []), ensure_ascii=False)}",
                "",
                f"**Attribution hint:** `{row['attribution_hint']}`",
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
    parser.add_argument("--temporary-retrieval", type=Path, default=DEFAULT_TEMP_RETRIEVAL)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    paths = {
        "manifest": args.run_dir / "run_manifest.json",
        "summary": args.run_dir / "run_summary.json",
        "retrieval": args.run_dir / "retrieval_report.json",
        "packs": args.run_dir / "evidence_packs.jsonl",
        "responses": args.run_dir / "responses.jsonl",
        "failures": args.run_dir / "failures.jsonl",
    }
    for path in [*paths.values(), args.questions]:
        if not path.is_file():
            raise FileNotFoundError(path)

    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    if manifest.get("scope") != "five frozen unseen PDFs — post-ingestion E5-D primary":
        raise ValueError("U7 evaluator accepts only the post-ingestion E5-D primary")
    if manifest.get("unseen_questions_sha256") != sha256(args.questions):
        raise ValueError("unseen question file hash differs from U7 run")
    if manifest.get("permanent_ingestion_already_completed") is not True:
        raise ValueError("U7 manifest does not record completed permanent ingestion")
    if manifest.get("frozen_e5_artifacts_modified") is not False:
        raise ValueError("U7 manifest unexpectedly records frozen E5 modification")

    questions = load_jsonl(args.questions)
    if len(questions) != 15:
        raise ValueError("expected 15 locked unseen questions")
    question_map = unique_map(questions, "question_id")
    retrieval_report = json.loads(paths["retrieval"].read_text(encoding="utf-8"))
    retrieval_map = unique_map(list(retrieval_report.get("questions", [])), "question_id")
    packs = unique_map(load_jsonl(paths["packs"]), "question_id")
    responses = unique_map(load_jsonl(paths["responses"]), "question_id")
    failures = unique_map(load_jsonl(paths["failures"]), "question_id")
    if set(responses) & set(failures):
        raise ValueError("U7 question appears in both responses and failures")
    if set(responses) | set(failures) != set(question_map):
        raise ValueError("U7 output membership differs from locked unseen questions")
    if set(retrieval_map) != set(question_map) or set(packs) != set(question_map):
        raise ValueError("U7 retrieval/evidence membership differs from locked unseen questions")

    temporary_map: dict[str, dict[str, Any]] = {}
    if args.temporary_retrieval.is_file():
        temp = json.loads(args.temporary_retrieval.read_text(encoding="utf-8"))
        temporary_map = unique_map(list(temp.get("questions", [])), "question_id")

    status_correct = status_checks = 0
    ref_hits = ref_checks = 0
    target_hits = target_checks = 0
    quote_checks = any_quote_hits = all_quote_hits = 0
    rows: list[dict[str, Any]] = []

    for question in questions:
        qid = str(question["question_id"])
        retrieval = retrieval_map[qid]
        pack = packs[qid]
        prompt_evidence = list((pack.get("prompt_payload") or {}).get("evidence", []))
        response = responses.get(qid)
        failure = failures.get(qid)
        hosted = (response or {}).get("answer") or {}
        answerable = bool(question["answerable_from_ad"])
        hosted_status = hosted.get("status") if response else None
        status_ok = None
        if response is not None:
            status_ok = (
                hosted_status == "answered"
                if answerable
                else hosted_status in {"insufficient_evidence", "conflicting_evidence"}
            )
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
            target_hit = any(
                str(citation.get("ad_number")) == str(question["target_ad_number"])
                for citation in citations
            )
            target_hits += int(bool(target_hit))

        any_quote, all_quotes, quote_results = quote_containment(question, prompt_evidence)
        if answerable:
            quote_checks += 1
            any_quote_hits += int(any_quote)
            all_quote_hits += int(all_quotes)

        retrieval_top5 = bool(retrieval.get("reference_page_any_at_5"))
        temp_row = temporary_map.get(qid, {})
        rows.append(
            {
                "question_id": qid,
                "stratum": question["stratum"],
                "category": question["category"],
                "authoring_query_mode": question["query_mode"],
                "post_ingestion_route_mode": retrieval.get("post_ingestion_route_mode"),
                "question": question["question"],
                "answerable_from_ad": answerable,
                "target_ad_number": question["target_ad_number"],
                "reference_pages": reference_pages,
                "reference_sections": question.get("reference_sections", []),
                "reference_answer": question.get("reference_answer", ""),
                "source_evidence": question.get("source_evidence", []),
                "prompt_evidence": prompt_evidence,
                "retrieval_reference_page_rank": retrieval.get("rank_at_20"),
                "retrieval_source_rank": retrieval.get("source_rank_at_20"),
                "retrieval_reference_in_top5": retrieval_top5,
                "retrieval_all_reference_pages_covered_at_5": bool(
                    retrieval.get("reference_page_all_covered_at_5")
                ),
                "temporary_reference_in_top5": temp_row.get("reference_page_any_at_5"),
                "temporary_all_reference_pages_covered_at_5": temp_row.get(
                    "reference_page_all_covered_at_5"
                ),
                "any_reference_quote_contained_in_top5": any_quote,
                "all_reference_quotes_contained_in_top5": all_quotes,
                "quote_results": quote_results,
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
                    "request_failure"
                    if failure is not None
                    else "post_ingestion_retrieval_support_missing_from_top5"
                    if answerable and not retrieval_top5
                    else "post_ingestion_passage_support_partial"
                    if answerable and not all_quotes
                    else "generation_can_be_evaluated"
                    if answerable
                    else "abstention_can_be_evaluated"
                ),
            }
        )

    summary = {
        "evaluator_version": EVALUATOR_VERSION,
        "selected_question_count": len(questions),
        "success_count": len(responses),
        "failure_count": len(failures),
        "request_success_rate": ratio(len(responses), len(questions)),
        "answerability_status_accuracy": ratio(status_correct, status_checks),
        "retrieval_overall": retrieval_report.get("overall"),
        "post_ingestion_route_mode_counts": retrieval_report.get(
            "post_ingestion_route_mode_counts", {}
        ),
        "reference_page_any_recall_at_5": retrieval_report.get(
            "reference_page_any_recall_at_5"
        ),
        "reference_page_full_coverage_at_5": retrieval_report.get(
            "reference_page_full_coverage_at_5"
        ),
        "any_reference_quote_containment_at_5": ratio(any_quote_hits, quote_checks),
        "all_reference_quotes_containment_at_5": ratio(all_quote_hits, quote_checks),
        "reference_page_citation_hit_rate": ratio(ref_hits, ref_checks),
        "target_ad_citation_hit_rate": ratio(target_hits, target_checks),
        "permanent_ingestion_condition": True,
        "policy": (
            "Post-final U7 unseen generalization evaluation. Automatic checks require human semantic review "
            "and cannot change the frozen E5 final result or the locked U3/U4 result."
        ),
    }

    output_dir = args.output_dir or (args.run_dir / "evaluation")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"refusing to overwrite U7 evaluation: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)
    report = {
        **summary,
        "unseen_questions_sha256": sha256(args.questions),
        "u7_run_summary_sha256": sha256(paths["summary"]),
        "retrieval_report_sha256": sha256(paths["retrieval"]),
        "evidence_packs_sha256": sha256(paths["packs"]),
        "responses_sha256": sha256(paths["responses"]),
        "failures_sha256": sha256(paths["failures"]),
        "rows": rows,
    }
    (output_dir / "automatic_evaluation.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    containment = {
        "version": "unseen-5-post-ingestion-reference-quote-containment-v1.0",
        "answerable_question_count": quote_checks,
        "any_reference_quote_containment_at_5": ratio(any_quote_hits, quote_checks),
        "all_reference_quotes_containment_at_5": ratio(all_quote_hits, quote_checks),
        "rows": [
            {
                "question_id": row["question_id"],
                "answerable_from_ad": row["answerable_from_ad"],
                "any_reference_quote_contained_in_top5": row[
                    "any_reference_quote_contained_in_top5"
                ],
                "all_reference_quotes_contained_in_top5": row[
                    "all_reference_quotes_contained_in_top5"
                ],
                "quote_results": row["quote_results"],
            }
            for row in rows
        ],
        "policy": "Diagnostic passage-support measure; it does not replace page-level retrieval metrics.",
    }
    (output_dir / "reference_quote_containment_diagnostic.json").write_text(
        json.dumps(containment, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    fields = [
        "question_id",
        "answer_correct",
        "requested_scope_complete",
        "material_conditions_complete",
        "compliance_time_complete",
        "exceptions_complete",
        "citation_support_correct",
        "unsupported_claims",
        "failure_attribution",
        "reviewer_notes",
    ]
    with (output_dir / "human_review.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({"question_id": row["question_id"]})
    (output_dir / "review_packet.md").write_text(
        render_packet(rows, summary), encoding="utf-8"
    )
    print(
        json.dumps({**summary, "output_dir": str(output_dir)}, indent=2, ensure_ascii=False)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
