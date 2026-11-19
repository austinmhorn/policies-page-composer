#!/usr/bin/env python3
"""Read-only existence check for the single Emergency Eyewash test record."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from policies_composer.config import load_project_env
from policies_composer.search_connector import get_document_state

DOC_ID = "birchstone-policy:41d82f87-9539-8022-b247-f885ef2344dd"

if __name__ == "__main__":
    load_project_env()
    print(json.dumps(get_document_state(DOC_ID), indent=2))
