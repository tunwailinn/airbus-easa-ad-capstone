"""Compatibility entry point for Layer C evidence-pack construction.

Canonical implementation: ``full_corpus_pipeline.layer_c.build_evidence_packs``.
"""

from full_corpus_pipeline.layer_c.build_evidence_packs import (
    EVIDENCE_DEPTH,
    EVIDENCE_PACK_VERSION,
    build_evidence_pack,
    canonical_json_bytes,
    load_jsonl_map,
    main,
    sha256_bytes,
)

__all__ = [
    "EVIDENCE_DEPTH",
    "EVIDENCE_PACK_VERSION",
    "build_evidence_pack",
    "canonical_json_bytes",
    "load_jsonl_map",
    "main",
    "sha256_bytes",
]

if __name__ == "__main__":
    raise SystemExit(main())
