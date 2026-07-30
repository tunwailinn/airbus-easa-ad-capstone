# Google Colab usage

The Step 2 package is stored under the project's read/write `metadata` folder.
The source PDFs in `corpus_raw` are not modified.

## 1. Mount Drive and set paths

```python
from google.colab import drive
from pathlib import Path

drive.mount("/content/drive")

PROJECT_ROOT = Path("/content/drive/MyDrive/Capstone_AD_Project")
STEP2_DIR = PROJECT_ROOT / "metadata" / "step2_ad_schema_and_guidelines"
ANNOTATIONS_DIR = PROJECT_ROOT / "metadata" / "annotations_v1"
ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)

assert STEP2_DIR.exists(), f"Step 2 package not found: {STEP2_DIR}"
print("Schema package:", STEP2_DIR)
print("Annotation output:", ANNOTATIONS_DIR)
```

If your Drive folder has a different project name, change only `PROJECT_ROOT`.

## 2. Install the validator dependency

```python
%pip -q install "jsonschema>=4.18,<5"
```

No GPU is needed for schema validation or manual annotation. A T4 becomes useful
later only if a local extraction model is used; Drive/PDF I/O and JSON validation
are CPU-bound.

## 3. Validate the supplied example

```python
import subprocess

result = subprocess.run(
    [
        "python3",
        str(STEP2_DIR / "validate_annotations.py"),
        "--strict",
        str(STEP2_DIR / "examples" / "2007-0178.annotation.json"),
    ],
    text=True,
    capture_output=True,
)
print(result.stdout)
if result.stderr:
    print(result.stderr)
result.check_returncode()
```

Expected output:

```text
PASS .../examples/2007-0178.annotation.json
```

## 4. Start a new draft without changing the template

```python
import json
from copy import deepcopy

template_path = STEP2_DIR / "blank_ad_annotation.json"
draft = json.loads(template_path.read_text(encoding="utf-8"))

# Replace this example name with the canonical AD number and file_instance_id.
output_path = ANNOTATIONS_DIR / "replace-with-ad-number.annotation.json"
output_path.write_text(
    json.dumps(deepcopy(draft), indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
print(output_path)
```

Populate source identifiers from `ad_corpus_manifest.parquet` or its CSV export,
then follow `annotation_guidelines.md`. Keep the blank template itself unchanged.

## 5. Validate drafts and approved records

Draft validation checks populated fields and references without requiring a
complete record:

```python
!python3 "{STEP2_DIR / 'validate_annotations.py'}" "{output_path}"
```

Before approving a gold record, run the stricter gate:

```python
!python3 "{STEP2_DIR / 'validate_annotations.py'}" --strict "{output_path}"
```

Do not set `record_status` to `approved` or `gold_record` to `true` merely to make
validation pass. Complete independent human review and evidence checks first.

## 6. Run the corpus-level gate

Before freezing a pilot or dataset split, validate all approved annotations in a
single command. This resolves correction targets and prevents revision families
or duplicate/near-duplicate clusters from crossing train, validation, and test:

```python
approved_paths = sorted(ANNOTATIONS_DIR.glob("*.annotation.json"))
assert approved_paths, "No annotation files found"

result = subprocess.run(
    [
        "python3",
        str(STEP2_DIR / "validate_annotations.py"),
        "--strict",
        *map(str, approved_paths),
    ],
    text=True,
    capture_output=True,
)
print(result.stdout)
if result.stderr:
    print(result.stderr)
result.check_returncode()
```

Do not use `--allow-unresolved-targets` for the final corpus-level gate.
