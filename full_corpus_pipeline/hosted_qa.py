"""Compatibility entry point for Layer C hosted QA.

Canonical implementation: ``full_corpus_pipeline.layer_c.hosted_qa``.
"""

from full_corpus_pipeline.layer_c.hosted_qa import (
    CONTRACT_PATH,
    HOSTED_QA_RUNNER_VERSION,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    Evidence,
    build_user_prompt,
    call_hosted_qa,
    evidence_from_pack,
    load_contract,
    main,
    validate_and_resolve_answer,
)

__all__ = [
    "CONTRACT_PATH",
    "HOSTED_QA_RUNNER_VERSION",
    "PROMPT_VERSION",
    "SYSTEM_PROMPT",
    "Evidence",
    "build_user_prompt",
    "call_hosted_qa",
    "evidence_from_pack",
    "load_contract",
    "main",
    "validate_and_resolve_answer",
]

if __name__ == "__main__":
    raise SystemExit(main())
