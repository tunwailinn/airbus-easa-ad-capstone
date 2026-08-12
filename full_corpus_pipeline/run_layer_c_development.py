"""Compatibility entry point for the Layer C development runner.

Canonical implementation: ``full_corpus_pipeline.layer_c.run_development``.
"""

from full_corpus_pipeline.layer_c.run_development import (
    BATCH_RUNNER_VERSION,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PACKS,
    file_sha256,
    load_packs,
    main,
    safe_run_name,
)

__all__ = [
    "BATCH_RUNNER_VERSION",
    "DEFAULT_OUTPUT_DIR",
    "DEFAULT_PACKS",
    "file_sha256",
    "load_packs",
    "main",
    "safe_run_name",
]

if __name__ == "__main__":
    raise SystemExit(main())
