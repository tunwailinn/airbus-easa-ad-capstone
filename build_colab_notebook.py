#!/usr/bin/env python3
"""Convert the supplied Step 1 Markdown workflow into a Colab notebook."""

from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path


SOURCE = Path(
    "/Users/tunwailin/.codex/attachments/"
    "6a6df6d7-0bf3-473a-a31b-c78e995878ef/pasted-text.txt"
)
OUTPUT = Path("01_build_ad_corpus_manifest.ipynb")
STRICT_AIRBUS_PATTERN = r"\bAirbus\s+S\.?\s*A\.?\s*S\.?\b"
AIRBUS_PATTERN = r"\bAirbus\b"
SUPERSEDURE_CELL_MARKER = "SUPERSEDURE_CONTEXT_RE = re.compile("
SUPERSEDURE_EXPLANATION_MARKER = "Why this is only a candidate detector:"
SCAN_CELL_MARKER = 'for path in tqdm(pdf_paths, desc="Processing AD PDFs"):'
AD_PARSING_CELL_MARKER = "AD_HEADER_RE = re.compile("
AD_PARSING_EXPLANATION_MARKER = "The parser first trusts the PDF header."
AD_PARSING_EXPLANATION_SOURCE = r'''The parser reads an anchored `AD No.` line from the first page and allows spaces around legacy separators such as `2007 - 0281` and `2008 – 0032`.

It separately parses the filename. If the two identifiers disagree, the cover-page header is retained but the row is flagged for manual review instead of silently grouping it with another AD.

Only when no anchored header is available does the parser use the filename, followed by a low-confidence generic fallback that is explicitly flagged for manual review.

# 8. Define date, correction and relationship extraction

Run:'''
AD_PARSING_CELL_SOURCE = r'''AD_HEADER_RE = re.compile(
    r"""
    ^[ \t]*
    (?:EASA\s+)?
    (?:EMERGENCY\s+)?
    AD\s+No\.?
    \s*[:#]?\s*
    (?P<year>(?:19|20)\d{2})
    \s*[-–—_]\s*
    (?P<number>\d{4})
    (?:\s*[-_]?\s*(?P<revision>R\d+))?
    (?:\s*[-_]?\s*(?P<emergency>E))?
    \b
    """,
    re.IGNORECASE | re.MULTILINE | re.VERBOSE,
)


GENERIC_AD_RE = re.compile(
    r"""
    \b
    (?P<year>(?:19|20)\d{2})
    [-–—_]
    (?P<number>\d{4})
    (?:[-_\s]?(?P<revision>R\d+))?
    (?:[-_\s]?(?P<emergency>E))?
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)


FILENAME_AD_RE = re.compile(
    r"""
    (?P<year>(?:19|20)\d{2})
    [-–—_]
    (?P<number>\d{4})
    (?:[-_\s]?(?P<revision>R\d+))?
    (?:[-_\s]?(?P<emergency>E))?
    """,
    re.IGNORECASE | re.VERBOSE,
)


def build_ad_number(match):
    """Create a standardized EASA AD number from a regex match."""
    year = match.group("year")
    number = match.group("number")

    revision = match.groupdict().get("revision")
    emergency = match.groupdict().get("emergency")

    ad_number = f"{year}-{number}"

    if revision:
        ad_number += revision.upper()

    if emergency and not revision:
        ad_number += "-E"

    return ad_number


def parse_ad_components(ad_number):
    """
    Convert 2023-0123R2 into:
    base_ad_number = 2023-0123
    revision_number = 2
    is_emergency = False
    """
    if not ad_number:
        return "", 0, False

    match = re.fullmatch(
        r"((?:19|20)\d{2}-\d{4})(?:R(\d+))?(-E)?",
        ad_number,
        flags=re.IGNORECASE,
    )

    if not match:
        return "", 0, False

    base_number = match.group(1).upper()
    revision_number = int(match.group(2) or 0)
    is_emergency = bool(match.group(3))

    return base_number, revision_number, is_emergency


def find_ad_number(text, file_name):
    """
    Search order:

    1. Anchored first-page ``AD No.`` line
    2. PDF filename
    3. Generic first-page match

    The header and filename are parsed independently so disagreements can
    be surfaced instead of silently accepting a historical body reference.
    """
    first_part = text[:5000] if text else ""

    header_boundary = re.search(
        r"^[ \t]*(?:Issued|Date)[ \t]*:",
        first_part,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    header_region = (
        first_part[:header_boundary.start()]
        if header_boundary
        else first_part
    )

    header_match = AD_HEADER_RE.search(header_region)
    filename_match = FILENAME_AD_RE.search(Path(file_name).stem)

    header_number = (
        build_ad_number(header_match)
        if header_match
        else ""
    )
    filename_number = (
        build_ad_number(filename_match)
        if filename_match
        else ""
    )

    if header_number:
        if filename_number and header_number != filename_number:
            return (
                header_number,
                "pdf_header_filename_mismatch",
                0.75,
            )

        return header_number, "pdf_header", 1.00

    if filename_number:
        return filename_number, "filename", 0.90

    generic_match = GENERIC_AD_RE.search(first_part)

    if generic_match:
        return build_ad_number(generic_match), "generic_first_page", 0.60

    return "", "not_found", 0.00


AD_NUMBER_REGRESSION_CASES = [
    (
        "EASA AIRWORTHINESS DIRECTIVE\n"
        "AD No.: 2007 - 0281\n"
        "Supersedure: This AD supersedes EASA AD 2006-0047",
        "2007-0281__easa_ad_2007_0281.pdf",
        "2007-0281",
        "pdf_header",
    ),
    (
        "EASA AIRWORTHINESS DIRECTIVE\n"
        "AD No.: 2008 – 0032\n"
        "Supersedure: EASA AD 2006-0108",
        "2008-0032__easa_ad_2008_0032.pdf",
        "2008-0032",
        "pdf_header",
    ),
    (
        "EASA AD No.: 2022-0096R2\nIssued: 12 April 2024",
        "2022-0096R2__EASA_AD_2022_0096_R2.pdf",
        "2022-0096R2",
        "pdf_header",
    ),
    (
        "Reason: SB A320-27-1164 was mandated by EASA AD 2006-0223.",
        "2007-0178__easa_ad_2007_0178.pdf",
        "2007-0178",
        "filename",
    ),
    (
        "Issued: 20 June 2007\n"
        "Supersedure:\n"
        "EASA AD No. 2006-0223 is superseded by this AD.",
        "2007-0178__easa_ad_2007_0178.pdf",
        "2007-0178",
        "filename",
    ),
]


for (
    regression_text,
    regression_file_name,
    expected_ad_number,
    expected_source,
) in AD_NUMBER_REGRESSION_CASES:
    parsed_number, parsed_source, _ = find_ad_number(
        regression_text,
        regression_file_name,
    )
    assert parsed_number == expected_ad_number
    assert parsed_source == expected_source


mismatch_number, mismatch_source, mismatch_confidence = find_ad_number(
    "EASA AD No.: 2024-0091R1\nIssued: 30 May 2024",
    "2024-0092__incorrect_filename.pdf",
)
assert mismatch_number == "2024-0091R1"
assert mismatch_source == "pdf_header_filename_mismatch"
assert mismatch_confidence == 0.75

print("AD number parser validation passed.")
'''
SUPERSEDURE_EXPLANATION_SOURCE = r'''Why these remain candidate relationships:

* The structured EASA `Supersedure:` field is authoritative, including when it says `None`.
* Explicit directional statements such as `This AD supersedes EASA AD ...` are also accepted because PDF text extraction can split or reorder the structured field.
* Negated statements, reverse `SUPERSEDED BY` stamps, approval numbers and broad keyword proximity are ignored.
* Automated extraction can still be affected by unusual PDF text layout, so exported links retain `manually_verified=False` until reviewed.

# 9. Scan all PDFs and construct initial records

Run:'''
SUPERSEDURE_CELL_SOURCE = r'''SUPERSEDURE_FIELD_LABEL_RE = re.compile(
    r"\b(?:Revision\s*/\s*)?Supersedure\s*:\s*",
    re.IGNORECASE,
)


SUPERSEDURE_FIELD_BOUNDARY_RE = re.compile(
    r"^(?:"
    r"ATA\s*\d{2}\b|"
    r"Manufacturer(?:\(s\))?\s*:|"
    r"Applicability\s*:|"
    r"Effective\s+Date\s*:|"
    r"Required\s+Action|"
    r"Compliance\s*:|"
    r"Reason\s*:|"
    r"TCDS\s+Number|"
    r"Foreign\s+AD\s*:|"
    r"(?:Revision\s*/\s*)?Supersedure\s*:"
    r")",
    re.IGNORECASE,
)


NO_SUPERSEDURE_RE = re.compile(
    r"^(?:none|not\s+applicable|n\s*/\s*a)\b",
    re.IGNORECASE,
)


POSITIVE_SUPERSEDURE_RE = re.compile(
    r"\b(?:"
    r"supersedes(?:\s+and\s+cancels)?|"
    r"superseded|"
    r"cancels\s+and\s+(?:replaces|supersedes)"
    r")\b",
    re.IGNORECASE,
)


REVERSE_OR_NEGATED_SUPERSEDURE_RE = re.compile(
    r"\b(?:"
    r"(?:this|the\s+present)\s+(?:EASA\s+)?AD\s+"
    r"(?:is|was)\s+superseded\s+by|"
    r"(?:does|is|are|was|were)\s+not\s+"
    r"(?:supersede|superseded)"
    r")\b",
    re.IGNORECASE,
)


EXPLICIT_FORWARD_SUPERSEDURE_RE = re.compile(
    r"\b(?:"
    r"(?:this|the\s+present|the\s+original)\s+"
    r"(?:new\s+)?(?:EASA\s+)?"
    r"(?:airworthiness\s+directive\s*(?:\(AD\))?|AD)|"
    r"the\s+original\s+issue\s+of\s+this\s+(?:EASA\s+)?AD"
    r")\s*,?\s*"
    r"(?:(?:which|also|hereby)\s+){0,2}"
    r"(?:"
    r"supersedes(?:\s+and\s+cancels)?|"
    r"cancels\s+and\s+(?:replaces|supersedes)"
    r")\s+"
    r"(?P<targets>[^.\n]{1,500})",
    re.IGNORECASE,
)


EXPLICIT_PASSIVE_SUPERSEDURE_RE = re.compile(
    # Begin at an AD marker instead of trying every character in the PDF.
    # The previous leading wildcard was bounded but still caused heavy
    # backtracking across the 1,809-document corpus.
    r"\b(?P<targets>(?:"
    r"(?:EASA\s+)?(?:Emergency\s+)?E?ADs?|"
    r"Airworthiness\s+Directives?"
    r")\b[^.\n]{1,300}?)\s+"
    r"(?:is|are|was|were)\s+(?:therefore\s+)?"
    r"superseded\s+by\s+"
    r"(?:this|the\s+present)\s+(?:EASA\s+)?AD\b",
    re.IGNORECASE,
)


EXPLICIT_RETAINS_SUPERSEDED_RE = re.compile(
    r"\b(?:this|the\s+present)\s+"
    r"(?:new\s+)?(?:EASA\s+)?AD\s+"
    r"retains\s+(?:the\s+)?requirements?\s+of\s+"
    r"(?P<targets>[^.\n]{1,500}?)\s*,?\s*"
    r"which\s+(?:is|are|was|were)\s+superseded\b",
    re.IGNORECASE,
)


AD_REFERENCE_MARKER_RE = re.compile(
    r"(?:"
    r"\b(?:EASA\s+)?(?:Emergency\s+)?E?ADs?\b|"
    r"\bAirworthiness\s+Directive\b"
    r")",
    re.IGNORECASE,
)


NON_AD_NUMBER_CONTEXT_RE = re.compile(
    r"(?:"
    r"approval(?:\s+number)?|"
    r"service\s+bulletin|"
    r"\bSB|"
    r"TCDS(?:\s+number)?"
    r")\s*(?:No\.?\s*)?$",
    re.IGNORECASE,
)


def extract_supersedure_field_values(text):
    """Read the authoritative EASA Supersedure header field."""
    lines = (text or "").splitlines()
    values = []

    for line_index, line in enumerate(lines):
        label_match = SUPERSEDURE_FIELD_LABEL_RE.search(line)

        if not label_match:
            continue

        value_parts = [line[label_match.end():].strip()]

        if NO_SUPERSEDURE_RE.match(value_parts[0]):
            values.append(value_parts[0])
            continue

        # A long field can wrap over a few PDF text lines. Stop before the
        # next structured header and never scan the body as part of the field.
        for continuation in lines[line_index + 1:line_index + 5]:
            continuation = continuation.strip()

            if not continuation:
                break

            if SUPERSEDURE_FIELD_BOUNDARY_RE.match(continuation):
                break

            if value_parts[-1].rstrip().endswith((".", ";")):
                break

            value_parts.append(continuation)

        values.append(" ".join(part for part in value_parts if part).strip())

    return values


def extract_referenced_ad_numbers(text, current_base):
    """Return AD-number references, excluding dates and approval numbers."""
    references = set()

    for ad_match in GENERIC_AD_RE.finditer(text or ""):
        full_prefix = (text or "")[:ad_match.start()]
        near_prefix = full_prefix[-100:]

        if NON_AD_NUMBER_CONTEXT_RE.search(near_prefix):
            continue

        # A plural marker can introduce a long list only once, for example
        # ``EASA ADs 2007-0300, 2008-0152 and 2009-0191``. Require that marker
        # before the number inside this already-bounded relation, while the
        # near-prefix check above still rejects approval and SB numbers.
        if not AD_REFERENCE_MARKER_RE.search(full_prefix):
            continue

        candidate = build_ad_number(ad_match)
        candidate_base, _, _ = parse_ad_components(candidate)

        if candidate_base and candidate_base != current_base:
            references.add(candidate)

    return references


def extract_supersedure_candidates(text, current_ad_number):
    """
    Extract high-precision supersedure candidates.

    Priority 1 is the structured EASA ``Supersedure:`` field. Strongly
    directional sentences whose subject is the current AD are also accepted
    because PDF extraction can split or reorder that field. Broad keyword
    proximity is intentionally not used.
    """
    current_base, _, _ = parse_ad_components(current_ad_number)
    candidates = set()
    evidence = set()

    field_values = extract_supersedure_field_values(text)

    if field_values:
        for field_value in field_values:
            normalized_value = re.sub(r"\s+", " ", field_value).strip()

            if not normalized_value:
                continue

            if NO_SUPERSEDURE_RE.match(normalized_value):
                continue

            if REVERSE_OR_NEGATED_SUPERSEDURE_RE.search(normalized_value):
                continue

            if not POSITIVE_SUPERSEDURE_RE.search(normalized_value):
                continue

            found = extract_referenced_ad_numbers(
                normalized_value,
                current_base,
            )

            if found:
                candidates.update(found)
                evidence.add(f"Supersedure: {normalized_value}"[:600])

    # PDF text layout can split or reorder a structured field. Independently
    # accept strongly directional sentences whose grammatical subject is the
    # current AD. This restores recall without returning to keyword proximity.
    relation_source = re.sub(r"\s+", " ", text or "")
    fallback_matches = [
        *EXPLICIT_FORWARD_SUPERSEDURE_RE.finditer(relation_source),
        *EXPLICIT_PASSIVE_SUPERSEDURE_RE.finditer(relation_source),
        *EXPLICIT_RETAINS_SUPERSEDED_RE.finditer(relation_source),
    ]

    if current_base:
        current_family_subject_re = re.compile(
            rf"\b(?:EASA\s+)?AD\s+{re.escape(current_base)}"
            r"(?:R\d+)?\s+(?:(?:also|hereby)\s+)?"
            r"superseded\s+(?P<targets>[^.\n]{1,500})",
            re.IGNORECASE,
        )
        fallback_matches.extend(
            current_family_subject_re.finditer(relation_source)
        )

    for relation_match in fallback_matches:
        relation_text = relation_match.group(0)

        if REVERSE_OR_NEGATED_SUPERSEDURE_RE.search(relation_text):
            continue

        found = extract_referenced_ad_numbers(
            relation_match.group("targets"),
            current_base,
        )

        if found:
            candidates.update(found)
            evidence.add(re.sub(r"\s+", " ", relation_text).strip()[:600])

    return sorted(candidates), sorted(evidence)
'''


def source_lines(text: str) -> list[str]:
    return [line + "\n" for line in text.rstrip().splitlines()]


def parse_cells(markdown: str) -> list[dict[str, object]]:
    cells: list[dict[str, object]] = []
    prose: list[str] = []
    code: list[str] = []
    fence_language = ""
    in_fence = False

    def flush_prose() -> None:
        if not prose:
            return
        text = "\n".join(prose).strip()
        prose.clear()
        if text:
            cells.append(
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": source_lines(text),
                }
            )

    def flush_code() -> None:
        text = "\n".join(code).strip("\n")
        code.clear()
        cells.append(
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": source_lines(text),
            }
        )

    for line in markdown.splitlines():
        opening = re.fullmatch(r"```\s*([^`]*)", line)
        if opening and not in_fence:
            flush_prose()
            fence_language = opening.group(1).strip().lower()
            in_fence = True
            continue

        if line.strip() == "```" and in_fence:
            if fence_language in {"python", "py"}:
                flush_code()
            else:
                prose.extend(
                    [f"```{fence_language}" if fence_language else "```", *code, "```"]
                )
                code.clear()
            fence_language = ""
            in_fence = False
            continue

        if in_fence:
            code.append(line)
        else:
            prose.append(line)

    if in_fence:
        raise ValueError("Unclosed Markdown code fence in supplied workflow")

    flush_prose()
    return cells


def apply_workflow_overrides(cells: list[dict[str, object]]) -> None:
    """Apply project-approved corrections to the supplied workflow."""
    replacements = 0
    ad_parser_replacements = 0
    ad_parser_explanation_replacements = 0
    supersedure_replacements = 0
    explanation_replacements = 0
    scan_replacements = 0

    for cell in cells:
        source = cell.get("source")
        if not isinstance(source, list):
            continue

        cell_text = "".join(source)

        if AD_PARSING_CELL_MARKER in cell_text:
            cell["source"] = source_lines(AD_PARSING_CELL_SOURCE)
            ad_parser_replacements += 1
            source = cell["source"]
            cell_text = "".join(source)

        if AD_PARSING_EXPLANATION_MARKER in cell_text:
            cell["source"] = source_lines(
                AD_PARSING_EXPLANATION_SOURCE
            )
            ad_parser_explanation_replacements += 1
            source = cell["source"]
            cell_text = "".join(source)

        if SCAN_CELL_MARKER in cell_text:
            scan_cell_text = cell_text
            scan_flag_anchor = '''    if not ad_number:
        review_flags.append("ad_number_not_found")

    if not is_airbus_sas:
'''
            scan_flag_replacement = '''    if not ad_number:
        review_flags.append("ad_number_not_found")

    if ad_number_source == "pdf_header_filename_mismatch":
        review_flags.append(
            "ad_number_header_filename_mismatch"
        )

    if ad_number_source == "generic_first_page":
        review_flags.append(
            "generic_ad_number_requires_review"
        )

    if not is_airbus_sas:
'''

            if scan_cell_text.count(scan_flag_anchor) != 1:
                raise ValueError(
                    "Expected one full-scan AD-number flag anchor."
                )

            scan_cell_text = scan_cell_text.replace(
                scan_flag_anchor,
                scan_flag_replacement,
            )
            cached_scan = r'''# Fast reruns reuse the prior manifest and extracted-text cache.
# Set this to True only when the source PDFs themselves have changed.
FORCE_RESCAN_PDFS = False

cached_manifest_path = OUTPUT_DIR / "corpus_manifest.parquet"
cached_text_path = OUTPUT_DIR / "corpus_extracted_text.parquet"
use_cached_corpus = (
    not FORCE_RESCAN_PDFS
    and cached_manifest_path.exists()
    and cached_text_path.exists()
)

if not FORCE_RESCAN_PDFS:
    missing_cache_paths = [
        str(path)
        for path in (cached_manifest_path, cached_text_path)
        if not path.exists()
    ]
    assert not missing_cache_paths, (
        "Cached rerun requested, but cache files are missing: "
        + ", ".join(missing_cache_paths)
        + ". Set FORCE_RESCAN_PDFS = True only if a full PDF rescan "
        "is intentional."
    )

if use_cached_corpus:
    cached_manifest = pd.read_parquet(cached_manifest_path)
    cached_text_df = pd.read_parquet(cached_text_path)

    assert len(cached_manifest) == len(pdf_paths)
    assert cached_manifest["file_instance_id"].is_unique
    assert cached_text_df["file_instance_id"].is_unique
    assert set(cached_manifest["file_instance_id"]) == set(
        cached_text_df["file_instance_id"]
    )

    records = cached_manifest.to_dict("records")
    text_cache = cached_text_df.to_dict("records")
    text_by_file_id = dict(zip(
        cached_text_df["file_instance_id"],
        cached_text_df["text"],
    ))
    normalized_text_by_file_id = {
        file_instance_id: normalize_text(text)
        for file_instance_id, text in text_by_file_id.items()
    }

    list_columns = [
        "supersedes_ad_numbers",
        "superseded_by_ad_numbers",
        "supersedure_evidence",
        "review_flags",
    ]

    for record in tqdm(records, desc="Refreshing cached parser and relationship fields"):
        for column in list_columns:
            value = record.get(column, "")

            if isinstance(value, list):
                parsed_value = value
            elif pd.isna(value) or value == "":
                parsed_value = []
            else:
                parsed_value = [
                    part.strip()
                    for part in str(value).split(" | ")
                    if part.strip()
                ]

            record[column] = parsed_value

        raw_text = text_by_file_id.get(record["file_instance_id"], "")
        (
            ad_number,
            ad_number_source,
            ad_number_confidence,
        ) = find_ad_number(
            raw_text,
            record.get("file_name", ""),
        )
        (
            base_ad_number,
            revision_number,
            is_emergency,
        ) = parse_ad_components(ad_number)
        (
            is_correction,
            correction_date_raw,
            correction_date,
        ) = extract_correction_information(raw_text)
        issue_date_raw, issue_date = extract_issue_date(raw_text)

        record["ad_number"] = ad_number
        record["base_ad_number"] = base_ad_number
        record["revision_number"] = revision_number
        record["is_emergency"] = is_emergency
        record["is_correction"] = is_correction
        record["correction_date_raw"] = correction_date_raw
        record["correction_date"] = correction_date
        record["issue_date_raw"] = issue_date_raw
        record["issue_date"] = issue_date
        record["ad_number_source"] = ad_number_source
        record["ad_number_confidence"] = ad_number_confidence

        supersedes_ad_numbers, supersedure_evidence = (
            extract_supersedure_candidates(
                raw_text,
                ad_number,
            )
        )
        record["supersedes_ad_numbers"] = supersedes_ad_numbers
        record["supersedure_evidence"] = supersedure_evidence

        is_airbus = bool(re.search(
            r"\bAirbus\b",
            raw_text,
            flags=re.IGNORECASE,
        ))
        record["is_airbus_sas_detected"] = is_airbus
        recomputed_flags = {
            "ad_number_not_found",
            "ad_number_header_filename_mismatch",
            "generic_ad_number_requires_review",
            "airbus_sas_not_detected",
            "same_ad_version_conflict",
        }
        review_flags = [
            flag
            for flag in record["review_flags"]
            if flag not in recomputed_flags
        ]

        if not ad_number:
            review_flags.append("ad_number_not_found")

        if ad_number_source == "pdf_header_filename_mismatch":
            review_flags.append(
                "ad_number_header_filename_mismatch"
            )

        if ad_number_source == "generic_first_page":
            review_flags.append(
                "generic_ad_number_requires_review"
            )

        if not is_airbus:
            review_flags.append("airbus_sas_not_detected")

        record["review_flags"] = sorted(set(review_flags))

    refreshed_ad_numbers = {
        record["file_instance_id"]: record["ad_number"]
        for record in records
    }
    for text_record in text_cache:
        text_record["ad_number"] = refreshed_ad_numbers.get(
            text_record["file_instance_id"],
            "",
        )

    print(
        "Using cached corpus for fast rerun:",
        len(records),
        "PDF records.",
    )
else:
'''
            cell["source"] = source_lines(
                cached_scan
                + textwrap.indent(scan_cell_text, "    ")
            )
            scan_replacements += 1
            source = cell["source"]
            cell_text = "".join(source)

        if SUPERSEDURE_CELL_MARKER in cell_text:
            cell["source"] = source_lines(SUPERSEDURE_CELL_SOURCE)
            supersedure_replacements += 1
            source = cell["source"]

        if SUPERSEDURE_EXPLANATION_MARKER in cell_text:
            cell["source"] = source_lines(SUPERSEDURE_EXPLANATION_SOURCE)
            explanation_replacements += 1
            source = cell["source"]

        for index, line in enumerate(source):
            if STRICT_AIRBUS_PATTERN in line:
                source[index] = line.replace(
                    STRICT_AIRBUS_PATTERN,
                    AIRBUS_PATTERN,
                )
                replacements += 1

    if replacements != 1:
        raise ValueError(
            "Expected to replace the strict Airbus S.A.S. regex once, "
            f"but replaced it {replacements} times."
        )

    if ad_parser_replacements != 1:
        raise ValueError(
            "Expected to replace the AD-number parser once, "
            f"but replaced it {ad_parser_replacements} times."
        )

    if ad_parser_explanation_replacements != 1:
        raise ValueError(
            "Expected to update the AD-number parser explanation once, "
            "but updated it "
            f"{ad_parser_explanation_replacements} times."
        )

    if supersedure_replacements != 1:
        raise ValueError(
            "Expected to replace the broad supersedure heuristic once, "
            f"but replaced it {supersedure_replacements} times."
        )

    if explanation_replacements != 1:
        raise ValueError(
            "Expected to update the supersedure explanation once, "
            f"but updated it {explanation_replacements} times."
        )

    if scan_replacements != 1:
        raise ValueError(
            "Expected to make the PDF scan cache-aware once, "
            f"but updated it {scan_replacements} times."
        )


def main() -> None:
    cells = parse_cells(SOURCE.read_text(encoding="utf-8"))
    apply_workflow_overrides(cells)

    notebook = {
        "cells": cells,
        "metadata": {
            "accelerator": "CPU",
            "colab": {
                "name": OUTPUT.name,
                "provenance": [],
            },
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.x",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    OUTPUT.write_text(
        json.dumps(notebook, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    code_cells = sum(cell["cell_type"] == "code" for cell in notebook["cells"])
    print(f"Created {OUTPUT} with {len(notebook['cells'])} cells ({code_cells} code).")


if __name__ == "__main__":
    main()
