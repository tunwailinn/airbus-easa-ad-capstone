from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import statistics
import time

from full_corpus_pipeline.assistant.runtime import AssistantRuntimeConfig, AviationDocumentAssistant
from full_corpus_pipeline.assistant_api.services import WarmInferenceService


QUESTIONS = [
    "For EASA AD 2011-0041R1, what actions had to be completed within 3 days after 14 March 2011?",
    "Which earlier directive does EASA AD 2011-0041R1 revise?",
    "Which A310 models are affected by EASA AD 2008-0008?",
    "What does EASA AD 2011-0142 require within 10 days?",
    "For EASA AD 2007-0173, what is the compliance time for reinforcement?",
    "Which Airbus directive requires reporting inspection results including no findings within 30 days after each inspection?",
    "Which directive supersedes AD 2019-0243 and applies to A340-211, -212, -213, -311, -312 and -313 aircraft?",
    "Which directive introduced a new AFM procedure applicable to all listed A318, A319, A320 and A321 aeroplanes?",
    "Which directive was republished because of a typo in a referenced Service Bulletin?",
    "Which directive revised an emergency AD and later accepted SB A380-31-8071?",
]


def top5(result: dict) -> list[str]:
    return [str(item["chunk_id"]) for item in result.get("evidence", [])[:5]]


async def main_async(args: argparse.Namespace) -> int:
    print("[compat] loading warm serving models once", flush=True)
    warm = WarmInferenceService(device=args.device)
    warm.load()

    print("[compat] initializing frozen-worker reference path", flush=True)
    legacy = AviationDocumentAssistant(
        AssistantRuntimeConfig(
            query_device=args.device,
            reranker_device=args.device,
            evidence_depth=5,
        )
    )

    rows = []
    for index, question in enumerate(QUESTIONS, 1):
        print(f"[compat] {index}/{len(QUESTIONS)} {question[:72]}", flush=True)
        old_start = time.perf_counter()
        old = legacy.retrieve(question)
        old_ms = (time.perf_counter() - old_start) * 1000

        warm_start = time.perf_counter()
        new = await warm.retrieve(question, [])
        warm_ms = (time.perf_counter() - warm_start) * 1000

        old_ids = top5(old)
        new_ids = top5(new)
        rows.append(
            {
                "question": question,
                "route": old.get("route", {}).get("mode"),
                "legacy_top5_chunk_ids": old_ids,
                "warm_top5_chunk_ids": new_ids,
                "top5_exact_match": old_ids == new_ids,
                "legacy_retrieval_ms": old_ms,
                "warm_retrieval_ms": warm_ms,
            }
        )

    matched = sum(bool(row["top5_exact_match"]) for row in rows)
    legacy_median = statistics.median(row["legacy_retrieval_ms"] for row in rows)
    warm_median = statistics.median(row["warm_retrieval_ms"] for row in rows)
    reduction = 1.0 - warm_median / legacy_median if legacy_median else 0.0
    report = {
        "version": "assistant-warm-serving-compatibility-v1.0",
        "question_count": len(rows),
        "top5_exact_match_count": matched,
        "top5_all_exact": matched == len(rows),
        "legacy_median_retrieval_ms": legacy_median,
        "warm_median_retrieval_ms": warm_median,
        "median_latency_reduction": reduction,
        "performance_target_60_percent_reduction_met": reduction >= 0.60,
        "device": warm.device,
        "rows": rows,
        "policy": "Post-evaluation serving compatibility only. Frozen E5 benchmark artifacts are not modified.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, indent=2))
    return 0 if report["top5_all_exact"] else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default="auto")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data_processed/serving/assistant_v2/warm_compatibility.json"),
    )
    return asyncio.run(main_async(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
