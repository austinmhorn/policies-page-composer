#!/usr/bin/env python3
"""Dry-run a single indexed policy; explicit write needs confirmed identity."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from policies_composer.config import load_project_env
from policies_composer.search_connector import TEST_IDENTITY, document_for_policy, upload_one
from policies_composer.validate import validate_policies
from scripts.render_workflow import load_policies


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=ROOT / "data" / "policies.json")
    parser.add_argument("--policy-number", default="5067")
    parser.add_argument("--manual", default="Emergency Procedures")
    parser.add_argument("--external-identity",
                        help="Confirmed Interact external identity for test-user visibility")
    parser.add_argument("--write", action="store_true", help="Upsert ONE policy into connector 2")
    parser.add_argument("--confirm-connector", type=int)
    args = parser.parse_args(argv)

    if args.write and (args.confirm_connector != 2 or args.external_identity != TEST_IDENTITY):
        parser.error("--write requires --confirm-connector 2 and --external-identity " + TEST_IDENTITY)
    if args.confirm_connector is not None and not args.write:
        parser.error("--confirm-connector requires --write")

    load_project_env()
    policies = load_policies(args.snapshot)
    validate_policies(policies, minimum_count=415)
    selected = [p for p in policies
                if p.number == args.policy_number and p.manual == args.manual]
    if len(selected) != 1:
        raise RuntimeError(f"Expected exactly one matching policy, found {len(selected)}")
    identity = args.external_identity or "DRY_RUN_IDENTITY_NOT_VALIDATED"
    doc = document_for_policy(selected[0], external_identity=identity)
    if not args.write:
        print(json.dumps({
            "mode": "DRY RUN - NO NETWORK OR WRITE",
            "connector_app_id": 2,
            "total_source_policies": len(policies),
            "selected": {
                "title": doc["Title"], "number": selected[0].number,
                "manual": selected[0].manual, "target_url": doc["Url"],
                "globally_unique_id": doc["GloballyUniqueId"],
            },
            "security": {
                "is_public": False, "external_identity_configured": bool(args.external_identity),
                "permission_mapping_verified": False,
            },
            "next": "Confirm external-identity mapping and visibility before --write",
        }, indent=2))
        return 0
    result = upload_one(doc)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
