"""Local configuration helpers for Layer C.

Secrets may be stored in a project-root ``.env`` file for local development.
The file is gitignored. Existing process environment variables always win over
values loaded from ``.env``.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"


def load_layer_c_env(path: Path = DEFAULT_ENV_PATH) -> bool:
    """Load local Layer C environment variables without overriding shell values."""
    if not path.exists():
        return False
    return bool(load_dotenv(dotenv_path=path, override=False))
