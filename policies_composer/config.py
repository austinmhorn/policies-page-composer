"""Load this project's local .env using python-dotenv, preserving special characters."""
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ENV = ROOT / "secrets" / ".env"


def load_project_env() -> bool:
    """Prefer the project-specific secrets file over stale shell exports.

    Missing file is acceptable for offline fixture tests. Secrets never get logged.
    """
    return load_dotenv(PROJECT_ENV, override=True)
