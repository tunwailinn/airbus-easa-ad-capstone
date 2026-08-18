#!/usr/bin/env python3
"""Command-line interface for the post-evaluation Airbus EASA AD assistant."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from full_corpus_pipeline.assistant.runtime import (
    AssistantRuntimeConfig,
    AviationDocumentAssistant,
    DEFAULT_DENSE_DIR,
    DEFAULT_INDEX,
)


def _format_page_range(citation: dict[str, Any]) -> str:
    start = int(citation["page_start"])
    end = int(citation["page_end"])
    return str(start) if start == end else f"{start}-{end}"


def render_human(result: dict[str, Any], *, show_evidence: bool) -> str:
    lines = [
        f"Status: {result.get('status')}",
        f"Route: {result.get('route', {}).get('mode', 'unknown')}",
    ]
    if result.get("answer"):
        lines.extend(["", str(result["answer"])])

    for label, key in (
        ("Conditions", "conditions"),
        ("Compliance time", "compliance_time"),
        ("Exceptions", "exceptions"),
    ):
        values = list(result.get(key) or [])
        if values:
            lines.append("")
            lines.append(f"{label}:")
            lines.extend(f"- {value}" for value in values)

    reason = result.get("reason_for_abstention")
    if reason:
        lines.extend(["", f"Reason: {reason}"])

    citations = list(result.get("citations") or [])
    if citations:
        lines.append("")
        lines.append("Citations:")
        for citation in citations:
            lines.append(
                "- "
                f"{citation['ad_number']} | p.{_format_page_range(citation)} | "
                f"{citation['section']} | {citation['evidence_id']}"
            )

    technical = result.get("technical_error")
    if technical:
        lines.extend(
            [
                "",
                f"Technical error: {technical.get('type')}: {technical.get('message')}",
            ]
        )

    if show_evidence:
        evidence = list(result.get("retrieval", {}).get("evidence") or [])
        if evidence:
            lines.extend(["", "Top evidence:"])
            for item in evidence:
                lines.extend(
                    [
                        "",
                        (
                            f"[{item['evidence_id']}] {item['ad_number']} "
                            f"p.{_format_page_range(item)} — {item['section']}"
                        ),
                        str(item["text"]).strip(),
                    ]
                )

    safety = result.get("safety") or {}
    if safety:
        lines.extend(
            [
                "",
                "Safety boundary:",
                f"- {safety.get('source_authority')}",
                f"- {safety.get('decision_boundary')}",
            ]
        )
    return "\n".join(lines)


def ask(
    assistant: AviationDocumentAssistant,
    question: str,
    *,
    retrieval_only: bool,
    output_json: bool,
    show_evidence: bool,
) -> None:
    result = assistant.answer(question, retrieval_only=retrieval_only)
    if output_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(render_human(result, show_evidence=show_evidence))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="*", help="Question to ask. Omit for interactive mode.")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--dense-dir", type=Path, default=DEFAULT_DENSE_DIR)
    parser.add_argument("--query-device", default="auto")
    parser.add_argument("--reranker-device", default="auto")
    parser.add_argument("--reranker-batch-size", type=int, default=2)
    parser.add_argument(
        "--retrieval-only",
        action="store_true",
        help="Skip DeepSeek and return only the frozen E5-D evidence.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument(
        "--show-evidence",
        action="store_true",
        help="Print the full top evidence passages in human-readable mode.",
    )
    args = parser.parse_args()

    assistant = AviationDocumentAssistant(
        AssistantRuntimeConfig(
            index_dir=args.index,
            dense_dir=args.dense_dir,
            query_device=args.query_device,
            reranker_device=args.reranker_device,
            reranker_batch_size=args.reranker_batch_size,
        )
    )

    question = " ".join(args.question).strip()
    if question:
        ask(
            assistant,
            question,
            retrieval_only=args.retrieval_only,
            output_json=args.json,
            show_evidence=args.show_evidence,
        )
        return 0

    print("Airbus EASA AD Assistant — interactive mode")
    print("Type :quit to exit.")
    while True:
        try:
            question = input("\nQuestion> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if question in {":quit", ":q", "quit", "exit"}:
            return 0
        if not question:
            continue
        ask(
            assistant,
            question,
            retrieval_only=args.retrieval_only,
            output_json=args.json,
            show_evidence=args.show_evidence,
        )


if __name__ == "__main__":
    raise SystemExit(main())
