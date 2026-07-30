#!/usr/bin/env python3
"""Generate the reproducible Google Colab control notebook for Step 3."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "03_build_review_gold_pilot.ipynb"


def markdown(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in source.strip().splitlines()],
    }


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in source.strip().splitlines()],
    }


cells = [
    markdown(
        """
# Step 3 - Build, review and validate the 30-AD pilot

This notebook operates on the frozen 15+15 selection in
`MyDrive/Capstone_AD_Project/metadata/step3_pilot_v1`.

It never writes to `corpus_raw`. The selection, official source PDFs and page
text are already hash-verified. The notebook prepares an isolated review
workspace, validates first-pass annotations, manages the 10 double-annotation
assignments and runs the final strict gold gate.

Important scientific boundary: Codex-generated first passes remain
`creation_method=hybrid`, `human_confirmed=false` and `gold_record=false`.
Only an independent human aviation reviewer/adjudicator may convert them to
approved gold records. Do not bypass that gate.

A T4 GPU is not needed for source verification, annotation or validation. It
is useful only later if you run a local LLM baseline.
"""
    ),
    code(
        """
!pip -q install "pypdf>=4,<7" "PyMuPDF>=1.24,<2" "jsonschema>=4.18,<5" "pandas>=2,<3"
"""
    ),
    markdown("## 1. Mount Drive and configure the frozen project paths"),
    code(
        """
from google.colab import drive
drive.mount('/content/drive')

from pathlib import Path
import json, shutil, subprocess, sys, zipfile
import pandas as pd

PROJECT_DIR = Path('/content/drive/MyDrive/Capstone_AD_Project')
METADATA_DIR = PROJECT_DIR / 'metadata'
STEP3_DRIVE = METADATA_DIR / 'step3_pilot_v1'
STEP2_DRIVE = METADATA_DIR / 'step2_ad_schema_and_guidelines'

SELECTION_CSV = STEP3_DRIVE / 'selection' / 'pilot_selection.csv'
SELECTION_JSON = STEP3_DRIVE / 'selection' / 'pilot_selection.json'
PDF_DIR = STEP3_DRIVE / 'source_pdfs'
PAGE_TEXT_DIR = STEP3_DRIVE / 'page_text'
PACKET_ZIP = STEP3_DRIVE / 'packets' / 'step3_annotation_packets_v1.zip'

for required in [SELECTION_CSV, SELECTION_JSON, PDF_DIR, PAGE_TEXT_DIR, PACKET_ZIP, STEP2_DRIVE]:
    assert required.exists(), f'Missing required Drive artifact: {required}'

print('Step 3 Drive root:', STEP3_DRIVE)
"""
    ),
    markdown("## 2. Create a fast local runtime (Drive remains the source of truth)"),
    code(
        """
RUNTIME = Path('/content/capstone_step3_runtime')
STEP3_RUNTIME = RUNTIME / 'step3_pilot'
STEP2_RUNTIME = RUNTIME / 'step2_ad_schema'
WORKSPACE = Path('/content/step3_annotation_workspace')

if RUNTIME.exists():
    shutil.rmtree(RUNTIME)
STEP3_RUNTIME.mkdir(parents=True)

for name in [
    'retrieve_pilot_sources.py',
    'prepare_annotation_packets.py',
    'build_section_index.py',
    'validate_step3_pilot.py',
    'validate_evidence_quotes.py',
    'audit_first_pass.py',
    'freeze_submission_manifest.py',
    'verify_submission_manifest.py',
    'compare_double_annotations.py',
    'audit_machine_adjudications.py',
    'assemble_human_review_queue.py',
    'summarize_strict_blockers.py',
    'run_regex_baseline.py',
    'prepare_llm_baseline_inputs.py',
    'evaluate_extractions.py',
]:
    shutil.copy2(STEP3_DRIVE / name, STEP3_RUNTIME / name)
shutil.copytree(STEP2_DRIVE, STEP2_RUNTIME)

if WORKSPACE.exists():
    shutil.rmtree(WORKSPACE)
WORKSPACE.mkdir(parents=True)
with zipfile.ZipFile(PACKET_ZIP) as archive:
    archive.extractall(WORKSPACE)

LOCAL_PILOT = WORKSPACE / 'step3_pilot'
print('Local review workspace:', LOCAL_PILOT)
"""
    ),
    markdown("## 3. Re-verify all 30 PDFs and 171 page records offline"),
    code(
        """
verify_cmd = [
    sys.executable, str(STEP3_RUNTIME / 'retrieve_pilot_sources.py'),
    '--offline',
    '--selection', str(SELECTION_CSV),
    '--pdf-dir', str(PDF_DIR),
    '--page-text-dir', str(PAGE_TEXT_DIR),
    '--report-json', '/content/source_verification_report.json',
    '--report-csv', '/content/source_verification_report.csv',
]
subprocess.run(verify_cmd, check=True)
report = json.loads(Path('/content/source_verification_report.json').read_text())
assert report['status'] == 'complete'
assert report['summary']['verified_pdfs'] == 30
assert report['summary']['verified_pages'] == 171
report['summary']
"""
    ),
    markdown("## 4. Inspect the frozen selection and double-annotation roster"),
    code(
        """
selection = pd.read_csv(SELECTION_CSV)
assert len(selection) == 30
assert selection.groupby('cohort').size().to_dict() == {'2006-2018': 15, '2019-2026': 15}
double_mask = selection['double_annotation'].astype(str).str.lower().eq('true')
assert double_mask.sum() == 10

display(selection[[
    'ad_number', 'cohort', 'family', 'ata', 'strata', 'page_count',
    'double_annotation', 'selection_status'
]])

print('Double annotation roster:')
display(selection.loc[double_mask, [
    'ad_number', 'cohort', 'strata', 'page_count'
]])

roster_path = STEP3_DRIVE / 'selection' / 'annotation_assignment_roster.csv'
if roster_path.exists():
    display(pd.read_csv(roster_path))
"""
    ),
    markdown(
        """
## 5. Annotation browser

Use the helper below to display the selected PDF and exact cached page text.
The `section_index.csv` is navigation only: a missing heading never proves
that a field is absent.
"""
    ),
    code(
        """
from IPython.display import display, Image, Markdown
import fitz

section_index = pd.read_csv(LOCAL_PILOT / 'packets' / 'section_index.csv')

def show_ad(ad_number: str, page_numbers=None):
    row = selection.loc[selection.ad_number == ad_number]
    if len(row) != 1:
        raise ValueError(f'AD not selected exactly once: {ad_number}')
    row = row.iloc[0]
    pdf_path = PDF_DIR / row.file_name
    display(Markdown(f'### {ad_number} - {row.strata}'))

    page_file = next(PAGE_TEXT_DIR.glob(f'{ad_number}__*.pages.jsonl'))
    pages = [json.loads(line) for line in page_file.read_text(encoding='utf-8').splitlines()]
    requested = set(page_numbers or [1])
    document = fitz.open(pdf_path)
    for page in pages:
        if page['page_number'] in requested:
            display(Markdown(f"#### PDF page {page['page_number']} - SHA {page['page_text_sha256'][:12]}"))
            pixmap = document.load_page(page['page_number'] - 1).get_pixmap(
                matrix=fitz.Matrix(1.5, 1.5), alpha=False
            )
            rendered = Path('/content') / f"{ad_number}-page-{page['page_number']}.png"
            pixmap.save(rendered)
            display(Image(filename=str(rendered), width=900))
            print(page['text'])
    document.close()

# Example known regression case:
show_ad('2026-0079', page_numbers=[1])
"""
    ),
    markdown(
        """
## 6. Save annotator submissions to Drive

Keep Annotator A and B isolated. Do not let B inspect A before both are
submitted. The prefilled files are templates only; every substantive field and
evidence span must be reviewed against the PDF.
"""
    ),
    code(
        """
SUBMITTED_A_DRIVE = STEP3_DRIVE / 'submitted' / 'annotator_a'
SUBMITTED_B_DRIVE = STEP3_DRIVE / 'submitted' / 'annotator_b'
SUBMITTED_A_DRIVE.mkdir(parents=True, exist_ok=True)
SUBMITTED_B_DRIVE.mkdir(parents=True, exist_ok=True)

def publish_submissions(local_dir: Path, drive_dir: Path):
    files = sorted(local_dir.glob('*.annotation.json'))
    for source in files:
        target = drive_dir / source.name
        if target.exists():
            raise FileExistsError(f'Refusing to overwrite frozen submission: {target}')
        shutil.copy2(source, target)
    print(f'Published {len(files)} immutable submissions to {drive_dir}')

# Run only after an annotator has completed and frozen the relevant local files:
# publish_submissions(LOCAL_PILOT / 'submitted' / 'annotator_a', SUBMITTED_A_DRIVE)
# publish_submissions(LOCAL_PILOT / 'submitted' / 'annotator_b', SUBMITTED_B_DRIVE)
"""
    ),
    markdown("## 7. Validate first-pass A and B streams separately"),
    code(
        """
VALIDATOR = STEP2_RUNTIME / 'validate_annotations.py'

def validate_stream(path: Path, strict=False):
    files = sorted(path.glob('*.annotation.json'))
    if not files:
        print('No annotations found in', path)
        return None
    cmd = [sys.executable, str(VALIDATOR)]
    if strict:
        cmd.append('--strict')
    cmd.extend(map(str, files))
    result = subprocess.run(cmd, text=True, capture_output=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    print('exit code:', result.returncode)
    return result.returncode

# Do not combine A and B in one call: they intentionally share record IDs.
validate_stream(SUBMITTED_A_DRIVE, strict=False)
validate_stream(SUBMITTED_B_DRIVE, strict=False)

def audit_stream(path: Path, expected: str):
    report_path = STEP3_DRIVE / 'validation' / f'annotator_{expected}_first_pass.json'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    audit = subprocess.run([
        sys.executable, str(STEP3_RUNTIME / 'audit_first_pass.py'),
        str(path), '--expected', 'all' if expected == 'a' else 'double',
        '--selection', str(SELECTION_JSON), '--report', str(report_path),
    ], text=True, capture_output=True)
    print(audit.stdout)
    if audit.stderr:
        print(audit.stderr)
    return audit.returncode

audit_stream(SUBMITTED_A_DRIVE, 'a')
audit_stream(SUBMITTED_B_DRIVE, 'b')

# Exact-quote/page-hash grounding check.
for stream in [SUBMITTED_A_DRIVE, SUBMITTED_B_DRIVE]:
    if list(stream.glob('*.annotation.json')):
        evidence = subprocess.run([
            sys.executable, str(STEP3_RUNTIME / 'validate_evidence_quotes.py'),
            str(stream), '--page-text-dir', str(PAGE_TEXT_DIR),
        ], text=True, capture_output=True)
        print(evidence.stdout)
        if evidence.stderr:
            print(evidence.stderr)

if (len(list(SUBMITTED_A_DRIVE.glob('*.annotation.json'))) == 30 and
        len(list(SUBMITTED_B_DRIVE.glob('*.annotation.json'))) == 10):
    freeze_result = subprocess.run([
        sys.executable, str(STEP3_RUNTIME / 'freeze_submission_manifest.py'),
        '--selection', str(SELECTION_JSON),
        '--roster', str(STEP3_DRIVE / 'selection' / 'annotation_assignment_roster.csv'),
        '--annotator-a', str(SUBMITTED_A_DRIVE),
        '--annotator-b', str(SUBMITTED_B_DRIVE),
        '--output-prefix', str(STEP3_DRIVE / 'submitted' / 'submission_manifest'),
    ], text=True, capture_output=True)
    print(freeze_result.stdout)
    if freeze_result.stderr:
        print(freeze_result.stderr)
    if freeze_result.returncode == 0:
        subprocess.run([
            sys.executable, str(STEP3_RUNTIME / 'verify_submission_manifest.py'),
            '--manifest', str(STEP3_DRIVE / 'submitted' / 'submission_manifest.json'),
            '--submitted-dir', str(STEP3_DRIVE / 'submitted'),
            '--selection', str(SELECTION_JSON),
            '--roster', str(STEP3_DRIVE / 'selection' / 'annotation_assignment_roster.csv'),
        ], check=True)
"""
    ),
    markdown(
        """
## 8. Adjudication and final strict gold gate

Preserve A and B unchanged. Put only the 30 independently reviewed and, where
needed, adjudicated final files in `gold/`. The strict gate requires exact
selection membership, page evidence, completion assertions, reviewer/event
history, `human_confirmed=true`, `record_status=approved` and
`gold_record=true`.
"""
    ),
    code(
        """
GOLD_DIR = STEP3_DRIVE / 'gold'
VALIDATION_DIR = STEP3_DRIVE / 'validation'
VALIDATION_DIR.mkdir(parents=True, exist_ok=True)

ADJUDICATION_DIR = STEP3_DRIVE / 'adjudication'
comparison_cmd = [
    sys.executable, str(STEP3_RUNTIME / 'compare_double_annotations.py'),
    '--selection', str(SELECTION_JSON),
    '--roster', str(STEP3_DRIVE / 'selection' / 'annotation_assignment_roster.csv'),
    '--annotator-a', str(SUBMITTED_A_DRIVE),
    '--annotator-b', str(SUBMITTED_B_DRIVE),
    '--output-dir', str(ADJUDICATION_DIR),
    '--require-complete',
]
comparison_result = subprocess.run(comparison_cmd, text=True, capture_output=True)
print(comparison_result.stdout)
if comparison_result.stderr:
    print(comparison_result.stderr)

MACHINE_CANDIDATES = ADJUDICATION_DIR / 'machine_candidates'
SINGLE_REVIEW_CANDIDATES = ADJUDICATION_DIR / 'single_review_candidates'
HUMAN_REVIEW_QUEUE = STEP3_DRIVE / 'human_review_queue'
if (comparison_result.returncode == 0 and
        len(list(MACHINE_CANDIDATES.glob('*.annotation.json'))) == 10):
    machine_audit = subprocess.run([
        sys.executable, str(STEP3_RUNTIME / 'audit_machine_adjudications.py'),
        '--selection', str(SELECTION_JSON),
        '--roster', str(STEP3_DRIVE / 'selection' / 'annotation_assignment_roster.csv'),
        '--candidate-dir', str(MACHINE_CANDIDATES),
        '--decision-dir', str(ADJUDICATION_DIR / 'decisions'),
        '--comparison', str(ADJUDICATION_DIR / 'double_annotation_comparison.json'),
        '--report', str(VALIDATION_DIR / 'machine_adjudication_audit.json'),
    ], text=True, capture_output=True)
    print(machine_audit.stdout)
    if machine_audit.stderr:
        print(machine_audit.stderr)
    machine_audit.check_returncode()
    queue_result = subprocess.run([
        sys.executable, str(STEP3_RUNTIME / 'assemble_human_review_queue.py'),
        '--selection', str(SELECTION_JSON),
        '--annotator-a', str(SUBMITTED_A_DRIVE),
        '--machine-candidates', str(MACHINE_CANDIDATES),
        '--single-review-candidates', str(SINGLE_REVIEW_CANDIDATES),
        '--output-dir', str(HUMAN_REVIEW_QUEUE), '--replace',
    ], text=True, capture_output=True)
    print(queue_result.stdout)
    if queue_result.stderr:
        print(queue_result.stderr)
    queue_result.check_returncode()

    queue_evidence = subprocess.run([
        sys.executable, str(STEP3_RUNTIME / 'validate_evidence_quotes.py'),
        str(HUMAN_REVIEW_QUEUE), '--page-text-dir', str(PAGE_TEXT_DIR),
    ], text=True, capture_output=True)
    print(queue_evidence.stdout)
    if queue_evidence.stderr:
        print(queue_evidence.stderr)
    queue_evidence.check_returncode()

    queue_strict_report = VALIDATION_DIR / 'human_review_queue_strict_blockers.json'
    queue_strict = subprocess.run([
        sys.executable, str(STEP3_RUNTIME / 'validate_step3_pilot.py'),
        str(HUMAN_REVIEW_QUEUE),
        '--selection', str(SELECTION_JSON),
        '--schema', str(STEP2_RUNTIME / 'easa_airbus_ad_annotation.schema.json'),
        '--report', str(queue_strict_report),
    ], text=True, capture_output=True)
    print(queue_strict.stdout)
    if queue_strict.stderr:
        print(queue_strict.stderr)
    print('pre-human strict exit code:', queue_strict.returncode)

    # The strict validator is expected to fail until a human approves the
    # records. This second gate must pass: it proves that only those expected
    # human-gold gates remain, with no fixable annotation defect hidden among
    # them.
    blocker_triage = subprocess.run([
        sys.executable, str(STEP3_RUNTIME / 'summarize_strict_blockers.py'),
        str(queue_strict_report),
        '--report', str(VALIDATION_DIR / 'human_review_queue_strict_blocker_summary.json'),
        '--markdown', str(VALIDATION_DIR / 'human_review_queue_strict_blocker_summary.md'),
    ], text=True, capture_output=True)
    print(blocker_triage.stdout)
    if blocker_triage.stderr:
        print(blocker_triage.stderr)
    blocker_triage.check_returncode()
else:
    print('Human-review queue not assembled: 10 machine adjudication candidates are required.')

gold_cmd = [
    sys.executable, str(STEP3_RUNTIME / 'validate_step3_pilot.py'),
    str(GOLD_DIR),
    '--selection', str(SELECTION_JSON),
    '--schema', str(STEP2_RUNTIME / 'easa_airbus_ad_annotation.schema.json'),
    '--report', str(VALIDATION_DIR / 'final_validation.json'),
]

# This must return 0 before the dataset is described as gold.
gold_result = subprocess.run(gold_cmd, text=True, capture_output=True)
print(gold_result.stdout)
if gold_result.stderr:
    print(gold_result.stderr)
print('strict gold exit code:', gold_result.returncode)
"""
    ),
    markdown(
        """
## 9. Extraction benchmark gate

Run regex/rules, zero-shot LLM and schema-guided LLM only after the strict gold
exit code is `0`. Keep all near-duplicate/base-number components in one split,
and never use any held-out AD as a prompt demonstration.

The evaluator reports exact scalar accuracy; precision, recall and F1 for
models/actions/publications/relationships and other set fields; token F1 for
unsafe-condition, applicability, requirements and compliance text; and
per-record scores. Preserve prompt/model/rule versions and processing time with
each output set.
"""
    ),
    code(
        """
if gold_result.returncode != 0:
    print('Baseline execution blocked: finish human review/adjudication and pass the strict gold gate first.')
else:
    print('Gold gate passed. Running the leakage-safe regex baseline.')
    LLM_INPUT = STEP3_DRIVE / 'baselines' / 'inputs' / 'pilot_llm_inputs.jsonl'
    subprocess.run([
        sys.executable, str(STEP3_RUNTIME / 'prepare_llm_baseline_inputs.py'),
        '--selection', str(SELECTION_JSON),
        '--page-text-dir', str(PAGE_TEXT_DIR),
        '--output', str(LLM_INPUT),
    ], check=True)
    REGEX_DIR = STEP3_DRIVE / 'baselines' / 'regex'
    subprocess.run([
        sys.executable, str(STEP3_RUNTIME / 'run_regex_baseline.py'),
        '--selection', str(SELECTION_JSON),
        '--page-text-dir', str(PAGE_TEXT_DIR),
        '--output-dir', str(REGEX_DIR),
    ], check=True)

    METRICS_DIR = STEP3_DRIVE / 'metrics'
    def score_method(name: str):
        prediction_dir = STEP3_DRIVE / 'baselines' / name
        predictions = sorted(prediction_dir.glob('*.json'))
        if len(predictions) != 30:
            print(f'{name}: expected 30 predictions, found {len(predictions)}; not scored')
            return
        subprocess.run([
            sys.executable, str(STEP3_RUNTIME / 'evaluate_extractions.py'),
            str(GOLD_DIR), str(prediction_dir), '--method', name,
            '--gold-validator', str(STEP3_RUNTIME / 'validate_step3_pilot.py'),
            '--output-dir', str(METRICS_DIR),
        ], check=True)

    for method in ['regex', 'zero_shot', 'schema_guided']:
        score_method(method)

    print('Add 30 zero-shot and 30 schema-guided prediction JSON files to their method folders, then rerun this cell.')
"""
    ),
]


notebook = {
    "cells": cells,
    "metadata": {
        "accelerator": "None",
        "colab": {"name": OUTPUT.name, "provenance": []},
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.x"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

OUTPUT.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"Wrote {OUTPUT}")
