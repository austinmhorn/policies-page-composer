#!/usr/bin/env python3
"""Read-only Interact Policies page verification; no changes or publication."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from policies_composer.interact import InteractClient
from policies_composer.page_target import target_id, verify_page


def main() -> None:
    page_id = target_id()
    client = InteractClient()
    page = client.get_page(page_id)
    print(json.dumps(verify_page(page, expected_id=page_id), indent=2))


if __name__ == "__main__":
    main()
