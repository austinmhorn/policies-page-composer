#!/usr/bin/env python3
"""Prepare or synchronize exactly one verified Interact Workplace Search identity."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from policies_composer.config import load_project_env
from policies_composer.search_connector import (
    TEST_EMAIL, TEST_IDENTITY, TEST_USER_GID,
    user_record_for_test, sync_test_user,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true",
                        help="Synchronize exactly one existing Interact user's external identity")
    parser.add_argument("--confirm-connector", type=int)
    parser.add_argument("--confirm-email")
    args = parser.parse_args(argv)
    if args.write and (args.confirm_connector != 2 or args.confirm_email != TEST_EMAIL):
        parser.error("--write requires --confirm-connector 2 and --confirm-email " + TEST_EMAIL)
    if not args.write and (args.confirm_connector is not None or args.confirm_email is not None):
        parser.error("Confirmation arguments require --write")
    record = user_record_for_test()
    if not args.write:
        print(json.dumps({
            "mode": "DRY RUN - NO NETWORK OR WRITE",
            "connector_app_id": 2,
            "email": TEST_EMAIL,
            "user_globally_unique_id": TEST_USER_GID,
            "external_identity": TEST_IDENTITY,
            "scope": "one existing account; no other users modified",
            "next": "Review identity mapping before explicit --write",
        }, indent=2))
        return 0
    load_project_env()
    print(json.dumps(sync_test_user(record), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
