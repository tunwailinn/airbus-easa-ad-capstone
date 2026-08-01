#!/usr/bin/env python3
from __future__ import annotations

import base64
import copy
import gzip
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path.cwd()
ANN = ROOT / "step3_extension_20_v1" / "human_review_working"
CHUNKS = ROOT / ".github" / "verbatim_delta_chunks"
MANIFEST = ROOT / ".github" / "verbatim_delta_manifest.json"

BEFORE = {
    "2006-0077__d5877768ebe69914.annotation.json": "2bf9828062882d5b2adbdd4bb93f14204158e4ae3e0d269ba1f57160f59e6eb7",
    "2007-0249__7a239ec5c306fa6d.annotation.json": "3ac914465e05434a49f33857c8b6b0f556461c968099791c84ea1d49ff795dba",
    "2008-0066__843fc74e8a4f44c0.annotation.json": "da2a66f623d772c4f85ce959203eb2d706f5fe28b1c446e630f60a176a4d0905",
    "2009-0171__6edf8772870b3a19.annotation.json": "5e43c0713b31d7578971156dee78275a90d3211dda2c69530f8920192d65c4d9",
    "2010-0271__2db3e9f8dfdadc71.annotation.json": "1e64a671b9bcf38e7777d6a1cb6cc276674660e2466a9bac568cf760ed327ef4",
    "2011-0098__ee69a71e72e4a031.annotation.json": "5bd3f84cdee96514aaa1718db387380d526efd35029b3ac7ed407837a9e2af2f",
    "2012-0259__71d534e47740b13c.annotation.json": "e1e0ba4833bfbf235c209aff5c592f6066763a7931f535aed8b7a4dbb75e9ebb",
    "2013-0011__5f652dd0aa52e54f.annotation.json": "000d11591f2a65b44357ee34aed9d8ed25f48c555d1896c62ce49a7c51f50b8f",
    "2016-0175__c13a622de38db424.annotation.json": "b824e1819772f56927670577b329cf96cb8c2f7b5e9049a93ea786f935308792",
    "2018-0246__0ffbff521ab9746f.annotation.json": "532d9ed289c1a3652fa35bdebe81c538e9a0f04469ea4ee3178067da075259f1",
    "2019-0188__1d1f6357de0f3352.annotation.json": "4047069388f9d8f67eda81005b86c60ad785f80a09bda6eebf4cedfa5a17dcad",
    "2020-0016__5c6e21ab23447af0.annotation.json": "73a3ff1055f0c4075348e9878c24871db8040e530ae1288a579f1e5a13fe96e2",
    "2021-0221__8aaaf372db377584.annotation.json": "3acaace02b9aa82d918f2647b9a5f76ef09129d13bf73311f5c4fa8edfe7cc05",
    "2021-0286__a36d7f18af6e7a27.annotation.json": "afa4cba06be22a26500dbeb9e670a9b3fd70db5d2df1a4e502bc25e8a6d1c121",
    "2022-0058__772cd84a0961a452.annotation.json": "336d647c53a8b911afefdeea4217a7c598bbf076c70ed372db45fbe9c0a1c050",
    "2023-0057__e17febf10e432eb9.annotation.json": "64ae987c4a3f1f43837037fb392a3edd40722ed8eb0b9f12451c597bb06bd56f",
    "2024-0001__dc59a5a0114b782d.annotation.json": "0604294132e2616758f37a025066b2489115917af112e4ab13753ce3c2bf4906",
    "2025-0138__5762b029d7edbc0c.annotation.json": "fa2aa190dee40c2cea3b16af1a99fad59866e23958dd568c8432099b92a94e7d",
    "2025-0181__b0e89b78cd668c9e.annotation.json": "5945f0d1952a194f8e65df0fbd4c5a7781c79571ff12d986d16949eed202f29a",
    "2026-0100__34edf2d1b2e65515.annotation.json": "360ba85ef9cc82f5d37d98c364b786f8e595789bc5d80ff5bd9ed284163eeb3e",
}

SCALAR_SOURCE_KEYS = {
    "raw_text", "raw_value", "raw_expression", "definition_text",
    "raw_reason_text", "action_text", "contact_text", "raw_name",
    "section_raw", "exact_quote",
}
LIST_SOURCE_KEYS = {
    "observed_events_or_defects", "causes", "unsafe_conditions",
    "potential_consequences", "affected_components", "intended_risk_mitigation",
    "objects_or_components", "conditions", "exclusions", "configuration_conditions",
}
EVIDENCE_LOCATION_KEYS = {
    "page_number", "printed_page_label", "page_text_sha256", "start_char",
    "end_char", "extraction_method", "quality", "annotation_note",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decode_pointer(pointer: str) -> list[str]:
    if not pointer.startswith("/"):
        raise ValueError(f"not a JSON pointer: {pointer}")
    return [p.replace("~1", "/").replace("~0", "~") for p in pointer[1:].split("/")]


def is_allowed(pointer: str) -> bool:
    parts = decode_pointer(pointer)
    leaf = parts[-1]
    if leaf in SCALAR_SOURCE_KEYS:
        return True
    if len(parts) >= 2 and parts[-1].isdigit() and parts[-2] in LIST_SOURCE_KEYS:
        return True
    if len(parts) >= 3 and parts[0] == "evidence_spans" and leaf in EVIDENCE_LOCATION_KEYS:
        return True
    if leaf == "text" and parts[0] in {"exceptions", "previous_action_credit", "relationships"}:
        return True
    return False


def get_at(root, parts):
    node = root
    for token in parts:
        node = node[int(token)] if isinstance(node, list) else node[token]
    return node


def set_at(root, parts, value):
    parent = get_at(root, parts[:-1]) if parts[:-1] else root
    leaf = parts[-1]
    if isinstance(parent, list):
        idx = int(leaf)
        if idx < 0 or idx >= len(parent):
            raise IndexError(parts)
        parent[idx] = value
    else:
        if leaf not in parent:
            raise KeyError("patch may not add schema keys: /" + "/".join(parts))
        parent[leaf] = value


def changed_pointers(a, b, path=""):
    if type(a) is not type(b):
        return {path or "/"}
    if isinstance(a, dict):
        if set(a) != set(b):
            return {path or "/"}
        out = set()
        for key in a:
            out |= changed_pointers(a[key], b[key], f"{path}/{key}")
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return {path or "/"}
        out = set()
        for i, (x, y) in enumerate(zip(a, b)):
            out |= changed_pointers(x, y, f"{path}/{i}")
        return out
    return set() if a == b else {path or "/"}


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected_final = manifest["expected_final_sha256"]
    if set(expected_final) != set(BEFORE):
        raise SystemExit("manifest/baseline file set mismatch")

    parts = sorted(CHUNKS.glob("part*"))
    if [p.name for p in parts] != [f"part{i:02d}" for i in range(5)]:
        raise SystemExit(f"unexpected compact delta parts: {[p.name for p in parts]}")
    encoded = "".join(p.read_text(encoding="utf-8").strip() for p in parts)
    delta = json.loads(gzip.decompress(base64.b64decode(encoded)).decode("utf-8"))
    if set(delta) != set(BEFORE):
        raise SystemExit("delta file set mismatch")
    edit_count = sum(len(ops) for ops in delta.values())
    if edit_count != manifest["expected_edits"]:
        raise SystemExit(f"expected {manifest['expected_edits']} edits, got {edit_count}")

    annotation_files = sorted(ANN.glob("*.annotation.json"))
    if len(annotation_files) != manifest["expected_files"]:
        raise SystemExit(f"expected {manifest['expected_files']} annotations, got {len(annotation_files)}")

    for name in sorted(delta):
        path = ANN / name
        if sha256(path) != BEFORE[name]:
            raise SystemExit(f"baseline SHA-256 mismatch: {name}")
        old = json.loads(path.read_text(encoding="utf-8"))
        new = copy.deepcopy(old)
        patch_paths = []
        for item in delta[name]:
            if not (isinstance(item, list) and len(item) == 2 and isinstance(item[0], str)):
                raise SystemExit(f"invalid delta operation in {name}: {item!r}")
            pointer, value = item
            if not is_allowed(pointer):
                raise SystemExit(f"disallowed source/evidence path in {name}: {pointer}")
            parts_ptr = decode_pointer(pointer)
            # Require the target to exist before replacement.
            get_at(new, parts_ptr)
            set_at(new, parts_ptr, value)
            patch_paths.append(pointer)

        actual_changes = changed_pointers(old, new)
        if actual_changes != set(patch_paths):
            raise SystemExit(
                f"change-set mismatch for {name}: actual={sorted(actual_changes)} expected={sorted(set(patch_paths))}"
            )

        if [r["requirement_id"] for r in old["requirements"]] != [r["requirement_id"] for r in new["requirements"]]:
            raise SystemExit(f"requirement IDs changed: {name}")
        if [r["paragraph_reference"] for r in old["requirements"]] != [r["paragraph_reference"] for r in new["requirements"]]:
            raise SystemExit(f"paragraph references changed: {name}")
        if new["classification"]["human_confirmed"] is not False:
            raise SystemExit(f"human_confirmed changed: {name}")
        if new["benchmark_metadata"]["gold_record"] is not False:
            raise SystemExit(f"gold_record changed: {name}")
        if new["annotation_metadata"]["record_status"] != "first_pass_complete":
            raise SystemExit(f"record_status changed: {name}")

        path.write_text(json.dumps(new, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        actual_final = sha256(path)
        if actual_final != expected_final[name]:
            raise SystemExit(f"final SHA-256 mismatch for {name}: {actual_final}")

    # Remove all delivery/inspection material so the PR ends with annotation JSON changes only.
    shutil.rmtree(ROOT / ".github" / "verbatim_delta_chunks", ignore_errors=True)
    shutil.rmtree(ROOT / ".github" / "verbatim_payload_chunks", ignore_errors=True)
    for rel in [
        ".github/verbatim_delta_manifest.json",
        ".github/apply_verbatim_delta.py",
        ".github/workflows/inspect-verbatim-delta.yml",
        ".github/workflows/apply-verbatim-delta.yml",
    ]:
        p = ROOT / rel
        if p.exists():
            p.unlink()

    print(f"applied {edit_count} guarded source-text/evidence edits across {len(delta)} annotations")


if __name__ == "__main__":
    main()
