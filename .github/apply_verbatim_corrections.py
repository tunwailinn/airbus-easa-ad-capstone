#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import json
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "step3_extension_20_v1" / "human_review_working"
PART_GLOB = ".github/verbatim_payload.part*"

TEXT_KEYS = {
    "raw_text", "raw_value", "raw_expression", "definition_text",
    "raw_reason_text", "action_text", "contact_text",
}
TEXT_LIST_KEYS = {
    "observed_events_or_defects", "causes", "unsafe_conditions",
    "potential_consequences", "affected_components",
    "intended_risk_mitigation", "objects_or_components", "conditions",
    "exclusions", "configuration_conditions",
}
ALLOWED_EVIDENCE_KEYS = {
    "exact_quote", "start_char", "end_char", "page_number",
    "printed_page_label", "page_text_sha256", "annotation_note",
}


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def verify_allowed_scope(old, new, path="") -> None:
    if type(old) is not type(new):
        raise ValueError(f"forbidden type change at {path}: {type(old)} -> {type(new)}")
    if isinstance(old, dict):
        if set(old) != set(new):
            raise ValueError(f"forbidden key change at {path}")
        for key in old:
            if old[key] == new[key]:
                continue
            child = f"{path}/{key}"
            if key in TEXT_KEYS:
                continue
            if key in TEXT_LIST_KEYS and isinstance(old[key], list) and isinstance(new[key], list):
                if len(old[key]) != len(new[key]):
                    raise ValueError(f"forbidden text-list length change at {child}")
                continue
            if key == "evidence_ids" and isinstance(old[key], list) and isinstance(new[key], list):
                continue
            if "/evidence_spans/" in child and key in ALLOWED_EVIDENCE_KEYS:
                continue
            verify_allowed_scope(old[key], new[key], child)
    elif isinstance(old, list):
        if len(old) != len(new):
            raise ValueError(f"forbidden list length change at {path}")
        for index, (left, right) in enumerate(zip(old, new)):
            if left != right:
                verify_allowed_scope(left, right, f"{path}/{index}")
    elif old != new:
        raise ValueError(f"forbidden value change at {path}: {old!r} -> {new!r}")


def safe_extract(archive: tarfile.TarFile, destination: Path) -> None:
    root = destination.resolve()
    for member in archive.getmembers():
        resolved = (destination / member.name).resolve()
        if root not in resolved.parents and resolved != root:
            raise ValueError(f"unsafe archive member: {member.name}")
    archive.extractall(destination)


def main() -> None:
    parts = sorted(ROOT.glob(PART_GLOB))
    if not parts:
        raise FileNotFoundError("verbatim correction payload parts are missing")
    encoded = b"".join(path.read_bytes() for path in parts)
    payload = base64.b64decode(encoded, validate=True)

    with tempfile.TemporaryDirectory(prefix="verbatim-fidelity-") as tmp_raw:
        tmp = Path(tmp_raw)
        archive_path = tmp / "payload.tar.gz"
        archive_path.write_bytes(payload)
        with tarfile.open(archive_path, "r:gz") as archive:
            safe_extract(archive, tmp)

        source_dir = tmp / "files"
        manifest_path = tmp / "corrected.sha256"
        manifest = {}
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            digest, filename = line.split(maxsplit=1)
            manifest[filename.strip()] = digest

        incoming = sorted(source_dir.glob("*.annotation.json"))
        existing = sorted(TARGET.glob("*.annotation.json"))
        if len(incoming) != 20 or {p.name for p in incoming} != {p.name for p in existing}:
            raise ValueError("payload must replace exactly the existing 20 annotation files")

        for source in incoming:
            raw = source.read_bytes()
            actual = hashlib.sha256(raw).hexdigest()
            if manifest.get(source.name) != actual:
                raise ValueError(f"payload digest mismatch for {source.name}")
            old = json.loads((TARGET / source.name).read_text(encoding="utf-8"))
            new = json.loads(raw.decode("utf-8"))
            verify_allowed_scope(old, new)
            if new.get("classification", {}).get("human_confirmed") is not False:
                raise ValueError(f"human_confirmed changed for {source.name}")
            if new.get("benchmark_metadata", {}).get("gold_record") is not False:
                raise ValueError(f"gold_record changed for {source.name}")
            shutil.copyfile(source, TARGET / source.name)

        # Recheck copied file digests.
        for filename, expected in manifest.items():
            actual = hashlib.sha256((TARGET / filename).read_bytes()).hexdigest()
            if actual != expected:
                raise ValueError(f"post-copy digest mismatch for {filename}")

    # Remove all temporary delivery tooling in the same commit.
    cleanup = [
        ROOT / ".github" / "apply_verbatim_corrections.py",
        ROOT / ".github" / "workflows" / "apply-verbatim-corrections.yml",
        ROOT / ".github" / "workflows" / "export-current-annotations.yml",
    ] + parts
    for path in cleanup:
        if path.exists():
            path.unlink()

    run("git", "config", "user.name", "github-actions[bot]")
    run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    run("git", "add", "step3_extension_20_v1/human_review_working", ".github")
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
        raise RuntimeError("no correction changes staged")
    run("git", "commit", "-m", "fix(step3): restore verbatim text and evidence fidelity")
    run("git", "push", "origin", f"HEAD:{subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip()}")


if __name__ == "__main__":
    main()
