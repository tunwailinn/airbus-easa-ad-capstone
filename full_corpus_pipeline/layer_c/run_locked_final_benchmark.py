#!/usr/bin/env python3
"""Validate the final benchmark lock, then run the one-time frozen primary benchmark."""

from __future__ import annotations

from full_corpus_pipeline.layer_c.validate_final_benchmark_lock import main as validate_lock
from full_corpus_pipeline.layer_c.run_final_benchmark import main as run_final


def main() -> int:
    validate_lock()
    return run_final()


if __name__ == "__main__":
    raise SystemExit(main())
