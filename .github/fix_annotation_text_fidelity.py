#!/usr/bin/env python3
"""Apply a conservative, fidelity-only correction to the 20 Step 3 annotations.

Permitted mutations:
- exact source-prose fields: raw_text, raw_value, raw_expression,
  definition_text, raw_reason_text, action_text, contact_text
- evidence exact_quote and its page location/hash fields

The script does not alter schema structure, IDs, enums, parsed dates, quantities,
classification confirmation, gold status, or record status.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import math
import re
import sys
import urllib.request
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

from pypdf import PdfReader

ROOT = Path("step3_extension_20_v1")
ANN_DIR = ROOT / "human_review_working"
REPORT_PATH = Path("annotation_text_fidelity_correction_report.json")

SOURCE_FIELDS = {
    "raw_text",
    "raw_value",
    "raw_expression",
    "definition_text",
    "raw_reason_text",
    "action_text",
    "contact_text",
}
EVIDENCE_LOCATION_FIELDS = {
    "exact_quote",
    "page_number",
    "page_text_sha256",
    "char_start",
    "char_end",
}
PROTECTED_STATUS_PATHS = {
    "/classification/human_confirmed",
    "/benchmark_metadata/gold_record",
    "/record_status",
}
STOP = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "by",
    "for", "from", "has", "have", "if", "in", "into", "is", "it", "its",
    "of", "on", "or", "that", "the", "their", "then", "there", "this",
    "to", "was", "were", "which", "with", "within", "without"
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_exact(text: str) -> str:
    """Normalize only harmless extraction differences allowed by the user."""
    text = text.replace("\u00ad", "").replace("\u00a0", " ")
    # Join words split by line-end hyphenation; preserve every other punctuation mark.
    text = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", text)
    return re.sub(r"\s+", " ", text).strip()


def tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+(?:[./_-][A-Za-z0-9]+)*", normalize_exact(text).lower())


def content_tokens(text: str) -> list[str]:
    return [t for t in tokens(text) if t not in STOP and len(t) > 1]


def numeric_tokens(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:[.,]\d+)*", normalize_exact(text)))


def overlap_metrics(target: str, candidate: str) -> tuple[float, float, float, float]:
    a = content_tokens(target)
    b = content_tokens(candidate)
    if not a or not b:
        return 0.0, 0.0, 0.0, 0.0
    ca, cb = Counter(a), Counter(b)
    overlap = sum((ca & cb).values())
    recall = overlap / max(1, sum(ca.values()))
    precision = overlap / max(1, sum(cb.values()))
    seq = SequenceMatcher(None, normalize_exact(target).lower(), normalize_exact(candidate).lower()).ratio()
    nums = numeric_tokens(target)
    num_cov = 1.0 if not nums else len(nums & numeric_tokens(candidate)) / len(nums)
    return recall, precision, seq, num_cov


def score_candidate(target: str, candidate: str, prefer_short: bool = False) -> float:
    recall, precision, seq, num_cov = overlap_metrics(target, candidate)
    if num_cov < 1.0:
        return -1.0
    score = 0.48 * recall + 0.20 * precision + 0.27 * seq + 0.05 * num_cov
    if prefer_short:
        ta = max(1, len(content_tokens(target)))
        cb = max(1, len(content_tokens(candidate)))
        score -= 0.04 * max(0.0, math.log(cb / ta))
    return score


def line_windows(text: str, max_lines: int = 42) -> Iterable[tuple[str, int, int]]:
    """Yield exact contiguous line windows and raw offsets."""
    matches = list(re.finditer(r".*(?:\n|$)", text))
    lines: list[tuple[str, int, int]] = []
    for m in matches:
        raw = m.group(0)
        if not raw:
            continue
        body = raw[:-1] if raw.endswith("\n") else raw
        if body.strip():
            lines.append((body, m.start(), m.start() + len(body)))
    n = len(lines)
    for i in range(n):
        for width in range(1, min(max_lines, n - i) + 1):
            j = i + width - 1
            start = lines[i][1]
            end = lines[j][2]
            yield text[start:end], start, end


def sentence_candidates(text: str) -> Iterable[str]:
    for part in re.split(r"(?<=[.!?;:])\s+(?=[(A-Z0-9])", normalize_exact(text)):
        part = part.strip()
        if part:
            yield part


def find_best_page_span(target: str, page_text: str) -> tuple[str, int, int, float, tuple[float, float, float, float]]:
    target_len = max(1, len(content_tokens(target)))
    best = ("", -1, -1, -1.0, (0.0, 0.0, 0.0, 0.0))
    for cand, start, end in line_windows(page_text):
        c_len = len(content_tokens(cand))
        if c_len < 2:
            continue
        if c_len > max(55, int(target_len * 2.8) + 18):
            continue
        metrics = overlap_metrics(target, cand)
        score = score_candidate(target, cand, prefer_short=False)
        # Prefer a compact window when scores are effectively tied.
        if score > best[3] + 1e-9 or (abs(score - best[3]) < 0.006 and len(cand) < len(best[0])):
            best = (cand, start, end, score, metrics)
    return best


def walk_values(value: Any, path: str = "") -> Iterable[tuple[str, str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}/{key}"
            yield child_path, key, child
            yield from walk_values(child, child_path)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from walk_values(child, f"{path}/{i}")


def find_source_pdf(annotation: dict[str, Any]) -> tuple[bytes, str, str]:
    urls: list[str] = []
    hashes: list[str] = []
    for path, key, value in walk_values(annotation):
        if isinstance(value, str):
            if value.startswith(("http://", "https://")) and "ad.easa.europa.eu" in value:
                urls.append(value)
            if re.fullmatch(r"[0-9a-fA-F]{64}", value) and "page_text_sha256" not in path:
                hashes.append(value.lower())
    urls = list(dict.fromkeys(urls))
    hashes = list(dict.fromkeys(hashes))
    errors = []
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 fidelity-audit"})
            with urllib.request.urlopen(req, timeout=60) as response:
                data = response.read()
            digest = sha256_bytes(data)
            if digest in hashes:
                return data, url, digest
            errors.append(f"{url}: downloaded sha256 {digest} not present in annotation")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{url}: {exc}")
    raise RuntimeError("Could not obtain a hash-matching source PDF. " + " | ".join(errors))


def extract_pages(pdf_bytes: bytes) -> dict[int, dict[str, Any]]:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages: dict[int, dict[str, Any]] = {}
    for number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages[number] = {
            "text": text,
            "normalized": normalize_exact(text),
            "sha256": sha256_text(text),
        }
    return pages


def evidence_index(annotation: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["evidence_id"]: item
        for item in annotation.get("evidence_spans", [])
        if isinstance(item, dict) and item.get("evidence_id")
    }


def repair_evidence(annotation: dict[str, Any], pages: dict[int, dict[str, Any]], changes: list[dict[str, Any]]) -> None:
    for idx, evidence in enumerate(annotation.get("evidence_spans", [])):
        quote = evidence.get("exact_quote") or ""
        page_no = evidence.get("page_number")
        if not quote or page_no not in pages:
            raise RuntimeError(f"Invalid evidence location for {evidence.get('evidence_id')}")
        declared = pages[page_no]
        if normalize_exact(quote) in declared["normalized"]:
            # Preserve permitted whitespace differences, but repair a stale hash.
            if evidence.get("page_text_sha256") != declared["sha256"]:
                old = evidence.get("page_text_sha256")
                evidence["page_text_sha256"] = declared["sha256"]
                changes.append({"path": f"/evidence_spans/{idx}/page_text_sha256", "old": old, "new": declared["sha256"], "reason": "page hash correction"})
            continue

        declared_best = find_best_page_span(quote, declared["text"])
        best_page = page_no
        best = declared_best
        # Search other pages only to correct a genuinely wrong page reference.
        for other_no, other in pages.items():
            if other_no == page_no:
                continue
            candidate = find_best_page_span(quote, other["text"])
            if candidate[3] > best[3] + 0.08:
                best_page, best = other_no, candidate

        candidate, start, end, score, metrics = best
        recall, _precision, _seq, num_cov = metrics
        if score < 0.48 or recall < 0.52 or num_cov < 1.0 or not candidate.strip():
            raise RuntimeError(
                f"No defensible contiguous source span for {evidence.get('evidence_id')} "
                f"on/near page {page_no}: score={score:.3f}, recall={recall:.3f}, numeric={num_cov:.3f}"
            )

        old_quote = quote
        evidence["exact_quote"] = candidate.strip()
        changes.append({
            "path": f"/evidence_spans/{idx}/exact_quote",
            "old": old_quote,
            "new": evidence["exact_quote"],
            "reason": "replace non-contiguous/reworded evidence with exact contiguous PDF span",
            "score": round(score, 4),
        })
        if best_page != page_no:
            evidence["page_number"] = best_page
            changes.append({"path": f"/evidence_spans/{idx}/page_number", "old": page_no, "new": best_page, "reason": "evidence occurs on another page"})
        page = pages[best_page]
        if evidence.get("page_text_sha256") != page["sha256"]:
            old_hash = evidence.get("page_text_sha256")
            evidence["page_text_sha256"] = page["sha256"]
            changes.append({"path": f"/evidence_spans/{idx}/page_text_sha256", "old": old_hash, "new": page["sha256"], "reason": "hash for corrected evidence page"})
        if "char_start" in evidence:
            old = evidence.get("char_start")
            evidence["char_start"] = start
            changes.append({"path": f"/evidence_spans/{idx}/char_start", "old": old, "new": start, "reason": "offset for corrected exact span"})
        if "char_end" in evidence:
            old = evidence.get("char_end")
            evidence["char_end"] = end
            changes.append({"path": f"/evidence_spans/{idx}/char_end", "old": old, "new": end, "reason": "offset for corrected exact span"})


def candidate_fragments(quote: str) -> list[str]:
    candidates = [quote.strip()]
    lines = [line.strip() for line in quote.splitlines() if line.strip()]
    for i in range(len(lines)):
        for width in range(1, min(9, len(lines) - i) + 1):
            candidates.append(" ".join(lines[i:i + width]))
    candidates.extend(sentence_candidates(quote))
    # Preserve order while deduplicating under the exact normalization rule.
    out: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        norm = normalize_exact(item)
        if norm and norm not in seen:
            seen.add(norm)
            out.append(item.strip())
    return out


def choose_exact_field_text(current: str, field_key: str, evidences: list[dict[str, Any]]) -> tuple[str, float]:
    quotes = [e.get("exact_quote", "") for e in evidences if e.get("exact_quote")]
    if not quotes:
        raise RuntimeError(f"No evidence quote available for non-verbatim {field_key}: {current[:120]}")

    # Long narrative/raw fields should retain the complete supporting source passage.
    full_passage = field_key in {"action_text", "raw_reason_text", "contact_text"} or len(content_tokens(current)) >= 18
    if full_passage:
        ranked = [(score_candidate(current, q, prefer_short=False), q) for q in quotes]
        score, selected = max(ranked, key=lambda item: item[0])
        if score < 0.33:
            raise RuntimeError(f"Low-confidence source passage for {field_key}: score={score:.3f}; text={current[:120]}")
        return selected.strip(), score

    candidates: list[str] = []
    for quote in quotes:
        candidates.extend(candidate_fragments(quote))
    ranked = [(score_candidate(current, c, prefer_short=True), c) for c in candidates]
    score, selected = max(ranked, key=lambda item: item[0])
    recall, _precision, _seq, num_cov = overlap_metrics(current, selected)
    if score < 0.30 or recall < 0.28 or num_cov < 1.0:
        # The complete exact evidence is safer than inventing/rewording a short phrase.
        ranked_full = [(score_candidate(current, q, prefer_short=False), q) for q in quotes]
        score, selected = max(ranked_full, key=lambda item: item[0])
    if score < 0.25:
        raise RuntimeError(f"No defensible source wording for {field_key}: score={score:.3f}; text={current[:120]}")
    return selected.strip(), score


def exactify_source_fields(
    value: Any,
    pages: dict[int, dict[str, Any]],
    ev_index: dict[str, dict[str, Any]],
    changes: list[dict[str, Any]],
    path: str = "",
    inherited_evidence_ids: list[str] | None = None,
) -> None:
    document_norm = " ".join(pages[p]["normalized"] for p in sorted(pages))
    if isinstance(value, dict):
        own_ids = value.get("evidence_ids")
        evidence_ids = own_ids if isinstance(own_ids, list) and own_ids else (inherited_evidence_ids or [])
        for key, child in list(value.items()):
            child_path = f"{path}/{key}"
            if key in SOURCE_FIELDS and isinstance(child, str) and child.strip():
                if normalize_exact(child) in document_norm:
                    continue
                related = [ev_index[eid] for eid in evidence_ids if eid in ev_index]
                replacement, score = choose_exact_field_text(child, key, related)
                # The replacement must be exact source wording on at least one cited evidence page.
                cited_page_norms = [pages[e["page_number"]]["normalized"] for e in related if e.get("page_number") in pages]
                if not any(normalize_exact(replacement) in page for page in cited_page_norms):
                    raise RuntimeError(f"Replacement for {child_path} is not exact on a cited page")
                value[key] = replacement
                changes.append({
                    "path": child_path,
                    "old": child,
                    "new": replacement,
                    "reason": "replace reworded source-derived prose with exact PDF wording",
                    "score": round(score, 4),
                    "evidence_ids": evidence_ids,
                })
            elif key != "evidence_spans":
                exactify_source_fields(child, pages, ev_index, changes, child_path, evidence_ids)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            exactify_source_fields(child, pages, ev_index, changes, f"{path}/{i}", inherited_evidence_ids)


def flatten(value: Any, path: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            out.update(flatten(child, f"{path}/{key}"))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            out.update(flatten(child, f"{path}/{i}"))
    else:
        out[path] = value
    return out


def assert_only_permitted_changes(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    a, b = flatten(before), flatten(after)
    changed = sorted(path for path in set(a) | set(b) if a.get(path) != b.get(path))
    for path in changed:
        leaf = path.rsplit("/", 1)[-1]
        in_evidence = path.startswith("/evidence_spans/")
        permitted = leaf in SOURCE_FIELDS or (in_evidence and leaf in EVIDENCE_LOCATION_FIELDS)
        if not permitted:
            raise RuntimeError(f"Prohibited mutation detected at {path}: {a.get(path)!r} -> {b.get(path)!r}")
    for protected in PROTECTED_STATUS_PATHS:
        if a.get(protected) != b.get(protected):
            raise RuntimeError(f"Protected status changed at {protected}")
    if b.get("/classification/human_confirmed") is not False:
        raise RuntimeError("classification.human_confirmed must remain false")
    if b.get("/benchmark_metadata/gold_record") is not False:
        raise RuntimeError("benchmark_metadata.gold_record must remain false")
    return changed


def verify_annotation(annotation: dict[str, Any], pages: dict[int, dict[str, Any]]) -> dict[str, int]:
    ev = evidence_index(annotation)
    evidence_checked = 0
    for item in annotation.get("evidence_spans", []):
        evidence_checked += 1
        page_no = item.get("page_number")
        if page_no not in pages:
            raise RuntimeError(f"Evidence {item.get('evidence_id')} cites missing page {page_no}")
        page = pages[page_no]
        if item.get("page_text_sha256") != page["sha256"]:
            raise RuntimeError(f"Evidence {item.get('evidence_id')} page hash mismatch")
        if normalize_exact(item.get("exact_quote") or "") not in page["normalized"]:
            raise RuntimeError(f"Evidence {item.get('evidence_id')} is not an exact contiguous page span")

    source_checked = 0
    document_norm = " ".join(pages[p]["normalized"] for p in sorted(pages))
    for path, key, value in walk_values(annotation):
        if key in SOURCE_FIELDS and isinstance(value, str) and value.strip():
            source_checked += 1
            if normalize_exact(value) not in document_norm:
                raise RuntimeError(f"Source-derived field remains non-verbatim at {path}")
    return {"evidence_checked": evidence_checked, "source_fields_checked": source_checked}


def process_file(path: Path, apply: bool) -> dict[str, Any]:
    before = json.loads(path.read_text(encoding="utf-8"))
    annotation = copy.deepcopy(before)
    pdf_bytes, source_url, pdf_sha = find_source_pdf(annotation)
    pages = extract_pages(pdf_bytes)
    changes: list[dict[str, Any]] = []

    repair_evidence(annotation, pages, changes)
    ev = evidence_index(annotation)
    exactify_source_fields(annotation, pages, ev, changes)
    changed_paths = assert_only_permitted_changes(before, annotation)
    counts = verify_annotation(annotation, pages)

    if apply and changed_paths:
        path.write_text(json.dumps(annotation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {
        "file": path.name,
        "source_url": source_url,
        "source_pdf_sha256": pdf_sha,
        "page_count": len(pages),
        "changed_path_count": len(changed_paths),
        "changed_paths": changed_paths,
        "changes": changes,
        **counts,
        "human_confirmed": annotation.get("classification", {}).get("human_confirmed"),
        "gold_record": annotation.get("benchmark_metadata", {}).get("gold_record"),
        "record_status": annotation.get("record_status"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    paths = sorted(ANN_DIR.glob("*.annotation.json"))
    if len(paths) != 20:
        raise RuntimeError(f"Expected exactly 20 annotation files, found {len(paths)}")

    report = {"mode": "apply" if args.apply else "verify", "files": [], "summary": {}}
    for path in paths:
        result = process_file(path, args.apply)
        report["files"].append(result)
        print(
            f"{path.name}: changed={result['changed_path_count']} "
            f"evidence={result['evidence_checked']} source_fields={result['source_fields_checked']}"
        )

    report["summary"] = {
        "files": len(report["files"]),
        "changed_paths": sum(item["changed_path_count"] for item in report["files"]),
        "evidence_checked": sum(item["evidence_checked"] for item in report["files"]),
        "source_fields_checked": sum(item["source_fields_checked"] for item in report["files"]),
        "human_confirmed_true": sum(item["human_confirmed"] is True for item in report["files"]),
        "gold_record_true": sum(item["gold_record"] is True for item in report["files"]),
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
