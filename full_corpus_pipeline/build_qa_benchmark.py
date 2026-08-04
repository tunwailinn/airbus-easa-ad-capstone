#!/usr/bin/env python3
"""Build and lock the 50-question QA benchmark from the 20-record test set."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "evaluation_sets/easa_airbus_ad_content_gold_50_v2"
SOURCE_DIR = ROOT / "gold_releases/easa_airbus_ad_gold_v2/annotations"
OUTPUT_DIR = ROOT / "evaluation_sets/easa_airbus_ad_qa_50_v2"
CATEGORY_COUNTS = {
    "identity_snapshot_lifecycle": 8,
    "applicability": 8,
    "required_action_compliance": 16,
    "referenced_publication": 6,
    "conditional_multi_passage": 6,
    "insufficient_conflict_abstention": 6,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact_reference(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def source_pages(source: dict[str, Any], field_path: str) -> list[int]:
    evidence_by_id = {item["evidence_id"]: item for item in source.get("evidence_spans", [])}
    evidence_ids: list[str] = []
    for assertion in source.get("field_assertions", []):
        if assertion.get("field_path") == field_path:
            evidence_ids.extend(assertion.get("evidence_ids", []))
    return sorted({int(evidence_by_id[item]["page_number"]) for item in evidence_ids if item in evidence_by_id})


def benchmark_requirements(source: dict[str, Any]) -> list[dict[str, Any]]:
    """Create private QA references without adding compliance fields to content JSON."""
    action_by_id = {
        item.get("requirement_id"): item.get("action_text")
        for item in source.get("requirements", [])
        if item.get("requirement_id") and item.get("action_text")
    }
    output = []
    for item in source.get("requirements", []):
        terminating = item.get("terminating_action") or {}
        reference = {
            "paragraph": item.get("paragraph_reference"),
            "action": item.get("action_text"),
            "conditions": item.get("conditions") or [],
            "compliance_wording": [
                rule.get("raw_text")
                for rule in item.get("compliance_rules", [])
                if rule.get("raw_text")
            ],
            "follow_on_actions": [
                action_by_id[item_id]
                for item_id in item.get("follow_on_requirement_ids", [])
                if item_id in action_by_id
            ],
            "terminating_action": terminating.get("action_text"),
        }
        output.append({key: value for key, value in reference.items() if value not in (None, [], "")})
    return output


def make_question(
    *, category: str, ad_number: str, question: str, answer: Any,
    pages: list[int], answerable: bool = True,
) -> dict[str, Any]:
    return {
        "question_id": "", "category": category, "question": question,
        "target_ad_number": ad_number, "reference_answer": compact_reference(answer),
        "reference_pages": pages, "answerable_from_ad": answerable,
    }


def build_questions(pairs: list[tuple[dict[str, Any], dict[str, Any]]]) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []

    identity_fields = [("issue_date", "What is the issue date"), ("effective_date", "What is the effective date"), ("subject", "What is the subject")]
    identity_pool = []
    for content, source in pairs:
        publication = content.get("publication", {})
        for field, wording in identity_fields:
            if publication.get(field):
                identity_pool.append(
                    make_question(
                        category="identity_snapshot_lifecycle", ad_number=content["ad_identity"]["ad_number"],
                        question=f"{wording} of AD {content['ad_identity']['ad_number']}?",
                        answer=publication[field], pages=source_pages(source, "/publication"),
                    )
                )
    questions.extend(identity_pool[:8])

    applicability_pool = []
    for content, source in pairs:
        if content.get("applicability"):
            applicability_pool.append(
                make_question(
                    category="applicability", ad_number=content["ad_identity"]["ad_number"],
                    question=f"Which aircraft and applicability conditions are stated in AD {content['ad_identity']['ad_number']}?",
                    answer=[item.get("raw_text") for item in source.get("applicability_groups", []) if item.get("raw_text")],
                    pages=source_pages(source, "/applicability_groups"),
                )
            )
    questions.extend(applicability_pool[:8])

    requirement_pool = []
    conditional_pool = []
    for content, source in pairs:
        ad_number = content["ad_identity"]["ad_number"]
        pages = source_pages(source, "/requirements")
        for requirement in benchmark_requirements(source):
            paragraph = requirement.get("paragraph", "the relevant paragraph")
            requirement_pool.append(
                make_question(
                    category="required_action_compliance", ad_number=ad_number,
                    question=f"What action and compliance timing does paragraph {paragraph} of AD {ad_number} require?",
                    answer={key: requirement[key] for key in ("action", "conditions", "compliance_wording", "follow_on_actions", "terminating_action") if key in requirement},
                    pages=pages,
                )
            )
            if any(requirement.get(key) for key in ("conditions", "follow_on_actions", "terminating_action")):
                conditional_pool.append(
                    make_question(
                        category="conditional_multi_passage", ad_number=ad_number,
                        question=f"For paragraph {paragraph} of AD {ad_number}, how do the condition, required action, follow-on action, and any terminating effect relate?",
                        answer=requirement, pages=pages,
                    )
                )
    questions.extend(requirement_pool[:16])

    publication_pool = []
    for content, source in pairs:
        references = content.get("referenced_publications")
        if references:
            ad_number = content["ad_identity"]["ad_number"]
            publication_pool.append(
                make_question(
                    category="referenced_publication", ad_number=ad_number,
                    question=f"Which referenced publications, including revisions and dates when printed, are identified by AD {ad_number}?",
                    answer=references, pages=source_pages(source, "/referenced_publications"),
                )
            )
    questions.extend(publication_pool[:6])
    questions.extend(conditional_pool[:6])

    abstention_templates = [
        ("What is the aircraft-specific calendar deadline today for a particular aircraft under AD {ad}?", "The AD alone does not provide the aircraft utilisation and embodiment history needed to calculate an aircraft-specific deadline."),
        ("What exact torque value from the referenced Service Bulletin must be used for AD {ad}?", "Insufficient information: Service Bulletin procedures are outside the indexed AD content unless the AD itself prints the torque value."),
        ("Has every affected aircraft worldwide already complied with AD {ad}?", "Insufficient information: fleet-wide compliance status is not stated in the AD."),
        ("Which maintenance organisation should perform the work for AD {ad}?", "Insufficient information: the AD does not select an operator-specific maintenance organisation."),
        ("Is AD {ad} legally current after the frozen corpus snapshot date?", "Insufficient information: the system represents the frozen snapshot and cannot establish post-snapshot legal currency."),
        ("Can the system authorize release to service after completing AD {ad}?", "No. The research prototype does not authorize maintenance or release to service."),
    ]
    for (template, answer), (content, _source) in zip(abstention_templates, pairs):
        ad_number = content["ad_identity"]["ad_number"]
        questions.append(
            make_question(
                category="insufficient_conflict_abstention", ad_number=ad_number,
                question=template.format(ad=ad_number), answer=answer, pages=[], answerable=False,
            )
        )

    counts = Counter(item["category"] for item in questions)
    if dict(counts) != CATEGORY_COUNTS:
        raise ValueError(f"unexpected category counts: {dict(counts)}")
    if len(questions) != 50:
        raise ValueError(f"expected 50 questions, found {len(questions)}")
    for index, item in enumerate(questions, 1):
        item["question_id"] = f"QA-{index:03d}"
    return questions


def main() -> int:
    if OUTPUT_DIR.exists() and any(OUTPUT_DIR.iterdir()):
        raise ValueError(f"refusing to overwrite locked benchmark: {OUTPUT_DIR}")
    split = json.loads((CONTENT_DIR / "split_manifest.json").read_text(encoding="utf-8"))
    test_rows = [row for row in split if row["split"] == "test"]
    pairs = []
    source_hashes = {}
    content_hashes = {}
    for row in test_rows:
        content_path = CONTENT_DIR / "records" / row["derived_filename"]
        source_path = SOURCE_DIR / row["source_gold_filename"]
        pairs.append((json.loads(content_path.read_text()), json.loads(source_path.read_text())))
        source_hashes[source_path.name] = sha256(source_path)
        content_hashes[content_path.name] = sha256(content_path)
    questions = build_questions(pairs)
    OUTPUT_DIR.mkdir(parents=True)
    with (OUTPUT_DIR / "questions.jsonl").open("w", encoding="utf-8") as handle:
        for question in questions:
            handle.write(json.dumps(question, ensure_ascii=False) + "\n")
    (OUTPUT_DIR / "questions.json").write_text(json.dumps(questions, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lock = {
        "name": "easa_airbus_ad_qa_50_v2", "question_count": 50,
        "category_counts": CATEGORY_COUNTS, "test_record_count": 20,
        "source_annotation_hashes": source_hashes, "content_record_hashes": content_hashes,
        "policy": "Do not tune extraction prompts or retrieval configuration against these locked questions.",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (OUTPUT_DIR / "benchmark_lock.json").write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "README.md").write_text(
        "# Locked QA benchmark v2\n\n"
        "This benchmark contains 50 evaluation questions over the locked 20-record test set. "
        "It evaluates whether corpus QA selects the correct AD, retrieves supporting pages, "
        "answers correctly, and abstains when the AD cannot support the requested conclusion. "
        "Complex compliance reference answers are derived privately from the immutable audit "
        "source because the content records preserve difficult wording without normalizing timing, "
        "conditions, exceptions, follow-on logic, and terminating effects. The QA system must "
        "answer those questions from retrieved original-PDF passages. No evidence span is copied "
        "into a content record. Do not tune on this benchmark.\n",
        encoding="utf-8",
    )
    print(f"Locked {len(questions)} QA questions in {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
