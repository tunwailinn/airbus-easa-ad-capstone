#!/usr/bin/env python3
import base64
import hashlib
import json
import zlib
from pathlib import Path

ROOT = Path("step3_extension_20_v1/human_review_working")
EXPECTED = {
    "2011-0098__ee69a71e72e4a031.annotation.json": "53933e051377860be12c8c632a172b38d21f1d79",
    "2012-0259__71d534e47740b13c.annotation.json": "d981f4caf8d51c0e8cc901377783931097fd46e2",
    "2013-0011__5f652dd0aa52e54f.annotation.json": "2222b2a5cb30e9b16dcc55bdb733cf32e93273b6",
    "2016-0175__c13a622de38db424.annotation.json": "887e06b47a9957dcee3354c05ded5c518f90f7d2",
    "2018-0246__0ffbff521ab9746f.annotation.json": "f62b39b4fa6f7be89816221bbddc3b55c41c14aa",
}


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def pointer_parts(path: str):
    return [part.replace("~1", "/").replace("~0", "~") for part in path.lstrip("/").split("/")]


def apply_operation(document, operation):
    parts = pointer_parts(operation["path"])
    current = document
    for part in parts[:-1]:
        current = current[int(part)] if isinstance(current, list) else current[part]
    key = int(parts[-1]) if isinstance(current, list) else parts[-1]
    if operation["op"] in {"add", "replace"}:
        current[key] = operation["value"]
    elif operation["op"] == "remove":
        current.pop(key)
    else:
        raise ValueError(f"Unsupported operation: {operation['op']}")


payload_text = Path(".github/next5_annotation_audit_payload.b64").read_text().strip()
payload = json.loads(zlib.decompress(base64.b64decode(payload_text)))
if set(payload) != set(EXPECTED):
    raise SystemExit("Payload path set does not match guarded target set")

for filename, operations in payload.items():
    path = ROOT / filename
    raw = path.read_bytes()
    actual = blob_sha(raw)
    if actual != EXPECTED[filename]:
        raise SystemExit(f"{filename}: expected {EXPECTED[filename]}, found {actual}; refusing overwrite")
    document = json.loads(raw)
    for operation in operations:
        apply_operation(document, operation)
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n")
    print(f"updated {path}")
