#!/usr/bin/env python3
"""Separate expected human-gold gates from fixable strict-validation blockers.

The Step 3 strict validator is intentionally run before human review.  Its raw
report therefore mixes two different things:

* expected gates that only a human review can satisfy; and
* annotation, evidence, schema, batch, or selection defects that should be
  fixed before asking a reviewer to approve the records.

This script classifies an existing ``validate_step3_pilot.py --report`` JSON,
writes concise JSON and Markdown summaries, and exits non-zero while any
pre-human blocker remains.  Unknown findings fail closed as pre-human blockers
so a newly introduced validator rule cannot be silently waived.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "validation" / "human_review_queue_strict_blockers.json"
DEFAULT_JSON_REPORT = (
    ROOT / "validation" / "human_review_queue_strict_blocker_summary.json"
)
DEFAULT_MARKDOWN_REPORT = (
    ROOT / "validation" / "human_review_queue_strict_blocker_summary.md"
)

EXPECTED_HUMAN_GATE = "expected_human_gate"
PRE_HUMAN_BLOCKER = "pre_human_blocker"
GLOBAL_RECORD = "__global__"

PER_RECORD_RE = re.compile(
    r"^(?P<label>.+?):\[(?P<stage>step2-schema|step2-strict|step3)\]\s*(?P<message>.*)$"
)
GLOBAL_RE = re.compile(
    r"^\[(?P<stage>step2-batch|step3-selection)\]\s*(?P<message>.*)$"
)
FIELD_INDEX_RE = re.compile(r"(/field_assertions/)[0-9]+")
POINTER_INDEX_RE = re.compile(r"/([0-9]+)(?=/|$)")
BRACKET_INDEX_RE = re.compile(r"\[[0-9]+\]")
FIELD_ASSERTION_MESSAGE_RE = re.compile(r"^/field_assertions/(?P<index>[0-9]+)")
REQUIREMENT_MESSAGE_RE = re.compile(r"^\$\.requirements\[(?P<index>[0-9]+)\]")


@dataclass(frozen=True)
class Finding:
    raw_error: str
    record: str
    label: str | None
    stage: str
    message: str
    blocker_class: str
    category: str
    reason: str


def _contains(message: str, *needles: str) -> bool:
    lowered = message.lower()
    return any(needle in lowered for needle in needles)


def classify_finding(stage: str, message: str) -> tuple[str, str, str]:
    """Return ``(class, category, reason)`` for one validator finding.

    Ordering is deliberate: safety/evidence/completeness problems take
    precedence over broad review-state patterns.  A rule that is not explicitly
    recognized is a pre-human blocker.
    """

    lowered = message.lower()

    if stage == "step2-schema":
        return (
            PRE_HUMAN_BLOCKER,
            "schema_or_json",
            "The annotation must satisfy the frozen schema before human approval.",
        )
    if stage == "step2-batch":
        return (
            PRE_HUMAN_BLOCKER,
            "batch_consistency",
            "Cross-record IDs, relationships, and split constraints are machine-checkable.",
        )
    if stage == "step3-selection":
        return (
            PRE_HUMAN_BLOCKER,
            "selection_integrity",
            "Frozen membership, provenance, and 15+15 cohort checks must pass first.",
        )
    if stage in {"load_or_config", "unparsed"}:
        return (
            PRE_HUMAN_BLOCKER,
            "load_config_or_unknown",
            "Load/configuration and unrecognized errors fail closed.",
        )

    # Unresolved values are not gold-review ceremony: they require an actual
    # decision, rationale, and evidence before approval.
    if _contains(lowered, "unclear/conflicting", "unresolved "):
        return (
            PRE_HUMAN_BLOCKER,
            "unresolved_or_conflicting_value",
            "Unclear, conflicting, or unresolved values require a substantive resolution.",
        )

    if _contains(
        lowered,
        "compliance_rules: required for approval",
        "compliance rule requires evidence",
        "compliance limit requires evidence",
    ):
        return (
            PRE_HUMAN_BLOCKER,
            "compliance_completeness",
            "Every requirement needs structured, grounded compliance rules and limits.",
        )

    # Evidence failures are fixable grounding defects.  The separate
    # "reviewed evidence assertion" Step 3 rule is handled later because it
    # means an existing assertion still awaits human acceptance/correction.
    evidence_defects = (
        "populated assertion requires evidence",
        "requires evidence",
        "required for approval",
        "state 'present' requires value, raw_text, and evidence",
        "state 'explicit_none' requires null value plus raw_text and evidence",
        "unresolved evidence id",
    )
    if any(phrase in lowered for phrase in evidence_defects) and (
        "requires a reviewed evidence assertion" not in lowered
    ):
        return (
            PRE_HUMAN_BLOCKER,
            "evidence_grounding",
            "Populated facts and assertions need traceable page evidence before review.",
        )

    if _contains(
        lowered,
        "populated section must have value_state=present",
        "empty section must be marked absent_in_source or not_applicable",
        "populated section-completion assertion requires evidence",
    ):
        return (
            PRE_HUMAN_BLOCKER,
            "section_completeness",
            "Section-completion state must agree with the populated annotation and evidence.",
        )

    if stage == "step2-strict":
        if "annotation_metadata.record_status: strict validation requires approved" in lowered:
            return (
                EXPECTED_HUMAN_GATE,
                "approval_status",
                "Approval is intentionally deferred until human review is complete.",
            )
        if "classification.human_confirmed: strict validation requires true" in lowered:
            return (
                EXPECTED_HUMAN_GATE,
                "human_confirmation",
                "A human must explicitly confirm the final classification.",
            )
        if "an approved record requires independent review" in lowered:
            return (
                EXPECTED_HUMAN_GATE,
                "independent_review",
                "The independent reviewer/approver is added during human review.",
            )
        if "an approved record requires an approved event" in lowered or (
            "each approved event must be performed by" in lowered
        ):
            return (
                EXPECTED_HUMAN_GATE,
                "approval_event",
                "An authorized reviewer records the approval event after review.",
            )
        if "approved records cannot retain" in lowered and "relationships" in lowered:
            return (
                EXPECTED_HUMAN_GATE,
                "relationship_human_resolution",
                "Candidate/conflicting relationships need explicit human resolution.",
            )

        return (
            PRE_HUMAN_BLOCKER,
            "strict_semantic_consistency",
            "This strict semantic failure is not merely an approval-state gate.",
        )

    if stage == "step3":
        if "/annotation_metadata/record_status:" in lowered:
            return (
                EXPECTED_HUMAN_GATE,
                "approval_status",
                "Final approved status is set only after human review.",
            )
        if "/annotation_metadata/creation_method:" in lowered:
            return (
                EXPECTED_HUMAN_GATE,
                "manual_gold_creation",
                "The reviewed gold label must be recorded as manually finalized.",
            )
        if "/benchmark_metadata/gold_record:" in lowered:
            return (
                EXPECTED_HUMAN_GATE,
                "gold_flag",
                "Gold status is set after review and approval.",
            )
        if "final pilot assertions must be accepted or corrected" in lowered:
            return (
                EXPECTED_HUMAN_GATE,
                "human_assertion_review",
                "A human must accept or correct every assertion.",
            )
        if "missing accepted/corrected human section-completion assertion" in lowered:
            return (
                EXPECTED_HUMAN_GATE,
                "human_section_review",
                "A human must explicitly mark every substantive section reviewed.",
            )
        if "populated important value requires a reviewed evidence assertion" in lowered:
            return (
                EXPECTED_HUMAN_GATE,
                "human_assertion_review",
                "The grounded assertion exists but still needs accepted/corrected review status.",
            )
        if "reviewed non-derived assertion requires an annotator" in lowered:
            return (
                EXPECTED_HUMAN_GATE,
                "human_assertion_provenance",
                "The reviewing human must be attached to the final assertion.",
            )
        if "independent reviewer/approver is missing" in lowered:
            return (
                EXPECTED_HUMAN_GATE,
                "independent_review",
                "The independent reviewer/approver is added during human review.",
            )
        if _contains(
            lowered,
            "selected double annotation requires distinct annotators a and b",
            "selected double annotation requires an adjudicator",
            "double annotation requires an adjudicated event with rationale",
        ):
            return (
                EXPECTED_HUMAN_GATE,
                "double_annotation_adjudication",
                "Selected records must retain independent A/B and adjudication provenance.",
            )

        # Missing initial annotation provenance/timestamps/submission is a bad
        # queue assembly, not something an approver should have to reconstruct.
        if _contains(
            lowered,
            "annotator a is missing",
            "is missing started_at",
            "is missing submitted_at",
            "each annotator must have a submitted event",
        ):
            return (
                PRE_HUMAN_BLOCKER,
                "annotation_provenance",
                "Initial annotation identity, timestamps, and submission events must be complete.",
            )

        return (
            PRE_HUMAN_BLOCKER,
            "step3_completeness_or_unknown",
            "This Step 3 finding is not an enumerated human-gold gate.",
        )

    return (
        PRE_HUMAN_BLOCKER,
        "load_config_or_unknown",
        "An unknown validator stage fails closed.",
    )


def parse_error(raw_error: str) -> Finding:
    """Parse and classify one raw strict-validator error string."""

    match = PER_RECORD_RE.match(raw_error)
    if match:
        label = match.group("label")
        stage = match.group("stage")
        message = match.group("message")
        filename = Path(label).name
        record = filename.removesuffix(".annotation.json") or filename
    else:
        match = GLOBAL_RE.match(raw_error)
        if match:
            label = None
            record = GLOBAL_RECORD
            stage = match.group("stage")
            message = match.group("message")
        else:
            label = None
            record = GLOBAL_RECORD
            stage = "load_or_config" if ":" in raw_error else "unparsed"
            message = raw_error

    blocker_class, category, reason = classify_finding(stage, message)
    return Finding(
        raw_error=raw_error,
        record=record,
        label=label,
        stage=stage,
        message=message,
        blocker_class=blocker_class,
        category=category,
        reason=reason,
    )


def normalized_signature(finding: Finding) -> str:
    """Return a stable grouping signature without record-specific indices."""

    message = FIELD_INDEX_RE.sub(r"\1N", finding.message)
    message = BRACKET_INDEX_RE.sub("[N]", message)
    message = POINTER_INDEX_RE.sub("/N", message)
    return f"[{finding.stage}] {message}"


def _category_rows(findings: Iterable[Finding]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Finding]] = defaultdict(list)
    for finding in findings:
        grouped[finding.category].append(finding)

    rows: list[dict[str, Any]] = []
    for category, members in grouped.items():
        signatures = Counter(normalized_signature(item) for item in members)
        rows.append(
            {
                "category": category,
                "error_count": len(members),
                "record_count": len({item.record for item in members}),
                "reason": members[0].reason,
                "signatures": [
                    {"count": count, "message": signature}
                    for signature, count in sorted(
                        signatures.items(), key=lambda item: (-item[1], item[0])
                    )
                ],
            }
        )
    return sorted(rows, key=lambda row: (-row["error_count"], row["category"]))


def _record_rows(
    findings: Iterable[Finding],
    contexts: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[Finding]] = defaultdict(list)
    for finding in findings:
        grouped[finding.record].append(finding)
    rows = []
    for record, members in sorted(grouped.items()):
        row = {
            "record": record,
            "error_count": len(members),
            "categories": dict(sorted(Counter(item.category for item in members).items())),
        }
        if contexts is not None:
            row["targets"] = sorted(
                {
                    contexts.get(item.raw_error, {}).get("display_target")
                    for item in members
                    if contexts.get(item.raw_error, {}).get("display_target")
                }
            )
        rows.append(row)
    return rows


def _load_annotation(
    label: str | None, cache: dict[str, dict[str, Any] | None]
) -> dict[str, Any] | None:
    if not label:
        return None
    if label not in cache:
        try:
            value = json.loads(Path(label).read_text(encoding="utf-8"))
            cache[label] = value if isinstance(value, dict) else None
        except (OSError, json.JSONDecodeError):
            cache[label] = None
    return cache[label]


def _finding_context(
    finding: Finding, cache: dict[str, dict[str, Any] | None]
) -> dict[str, Any]:
    """Attach concise target details when the source annotation is available."""

    validator_target = finding.message.split(":", 1)[0]
    context: dict[str, Any] = {
        "validator_target": validator_target,
        "display_target": validator_target,
    }
    record = _load_annotation(finding.label, cache)
    if record is None:
        return context

    assertion_match = FIELD_ASSERTION_MESSAGE_RE.match(finding.message)
    if assertion_match:
        index = int(assertion_match.group("index"))
        assertions = record.get("field_assertions") or []
        if index < len(assertions) and isinstance(assertions[index], dict):
            assertion = assertions[index]
            assertion_id = assertion.get("assertion_id") or f"assertion[{index}]"
            field_path = assertion.get("field_path") or "<missing-field-path>"
            context.update(
                {
                    "assertion_index": index,
                    "assertion_id": assertion.get("assertion_id"),
                    "field_path": assertion.get("field_path"),
                    "value_state": assertion.get("value_state"),
                    "origin": assertion.get("origin"),
                    "display_target": f"{assertion_id} {field_path}",
                }
            )
        return context

    requirement_match = REQUIREMENT_MESSAGE_RE.match(finding.message)
    if requirement_match:
        index = int(requirement_match.group("index"))
        requirements = record.get("requirements") or []
        if index < len(requirements) and isinstance(requirements[index], dict):
            requirement = requirements[index]
            requirement_id = requirement.get("requirement_id") or f"requirement[{index}]"
            context.update(
                {
                    "requirement_index": index,
                    "requirement_id": requirement.get("requirement_id"),
                    "paragraph_reference": requirement.get("paragraph_reference"),
                    "action_types": requirement.get("action_types"),
                    "display_target": f"{requirement_id} compliance_rules",
                }
            )
    return context


def build_summary(source_path: Path, source: dict[str, Any], source_bytes: bytes) -> dict[str, Any]:
    errors = source.get("errors")
    if not isinstance(errors, list) or not all(isinstance(item, str) for item in errors):
        raise ValueError("input report must contain an errors array of strings")

    findings = [parse_error(item) for item in errors]
    human = [item for item in findings if item.blocker_class == EXPECTED_HUMAN_GATE]
    pre_human = [item for item in findings if item.blocker_class == PRE_HUMAN_BLOCKER]
    annotation_cache: dict[str, dict[str, Any] | None] = {}
    pre_human_contexts = {
        item.raw_error: _finding_context(item, annotation_cache) for item in pre_human
    }
    records_with_pre_human = sorted(
        {item.record for item in pre_human if item.record != GLOBAL_RECORD}
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_report": str(source_path.resolve()),
        "source_report_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "source_validator_passed": bool(source.get("passed")),
        "record_count": source.get("record_count"),
        "selection_count": source.get("selection_count"),
        "total_error_count": len(findings),
        "expected_human_gate_count": len(human),
        "pre_human_blocker_count": len(pre_human),
        "records_with_pre_human_blockers": records_with_pre_human,
        "record_count_with_pre_human_blockers": len(records_with_pre_human),
        "ready_for_human_review": not pre_human,
        "classification_policy": {
            "unknown_findings": "pre_human_blocker",
            "exit_zero_when": "pre_human_blocker_count == 0",
            "note": (
                "A zero exit means only expected human-gold gates remain; it does not "
                "mean the final gold pilot passes strict validation."
            ),
        },
        "expected_human_gates": {
            "categories": _category_rows(human),
            "records": _record_rows(human),
        },
        "pre_human_blockers": {
            "categories": _category_rows(pre_human),
            "records": _record_rows(pre_human, pre_human_contexts),
            "findings": [
                {
                    "record": item.record,
                    "stage": item.stage,
                    "category": item.category,
                    "message": item.message,
                    "context": pre_human_contexts[item.raw_error],
                    "raw_error": item.raw_error,
                }
                for item in pre_human
            ],
        },
    }


def _markdown_table(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["None."]
    output = ["| Category | Errors | Records |", "|---|---:|---:|"]
    output.extend(
        f"| `{row['category']}` | {row['error_count']} | {row['record_count']} |"
        for row in rows
    )
    return output


def render_markdown(summary: dict[str, Any]) -> str:
    ready = summary["ready_for_human_review"]
    outcome = (
        "PASS: only expected human-gold gates remain."
        if ready
        else (
            "FAIL: fix pre-human blockers before asking reviewers to approve the queue."
        )
    )
    pre = summary["pre_human_blockers"]
    human = summary["expected_human_gates"]
    lines = [
        "# Human-review queue strict-blocker triage",
        "",
        f"**Outcome:** {outcome}",
        "",
        f"- Records loaded: {summary['record_count']}",
        f"- Frozen selection rows: {summary['selection_count']}",
        f"- Raw strict-validator errors: {summary['total_error_count']}",
        f"- Expected human-gold gates: {summary['expected_human_gate_count']}",
        f"- Fixable pre-human blockers: {summary['pre_human_blocker_count']}",
        f"- Records with pre-human blockers: {summary['record_count_with_pre_human_blockers']}",
        "",
        "## Fix before human approval",
        "",
        *_markdown_table(pre["categories"]),
        "",
    ]
    if pre["records"]:
        lines.extend(
            [
                "| Record | Findings | Exact targets |",
                "|---|---:|---|",
                *(
                    f"| `{row['record']}` | {row['error_count']} | "
                    + ", ".join(f"`{target}`" for target in row.get("targets", []))
                    + " |"
                    for row in pre["records"]
                ),
                "",
            ]
        )
    lines.extend(
        [
            "## Expected human-gold gates",
            "",
            *_markdown_table(human["categories"]),
            "",
            "These findings should disappear only after the human accepts or corrects "
            "the assertions, completes section markers, adds independent review and "
            "approval provenance, sets manual/approved/human-confirmed/gold state, and "
            "finishes required A/B adjudication.",
            "",
            "## Exit contract",
            "",
            "The summarizer exits `1` while any pre-human blocker remains and `0` when "
            "the regenerated validator report contains only expected human gates (or no "
            "errors). Unknown future findings fail closed as pre-human blockers.",
            "",
            f"Source SHA-256: `{summary['source_report_sha256']}`",
            "",
        ]
    )
    return "\n".join(lines)


def _load_report(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("input report root must be a JSON object")
    return value, raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_JSON_REPORT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN_REPORT)
    args = parser.parse_args(argv)

    try:
        source, raw = _load_report(args.input)
        summary = build_summary(args.input, source, raw)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(render_markdown(summary), encoding="utf-8")

    passed = summary["ready_for_human_review"]
    print(
        f"{'PASS' if passed else 'FAIL'} strict-blocker triage: "
        f"{summary['pre_human_blocker_count']} pre-human blocker(s), "
        f"{summary['expected_human_gate_count']} expected human gate(s)"
    )
    print(f"JSON report: {args.report}")
    print(f"Markdown report: {args.markdown}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
