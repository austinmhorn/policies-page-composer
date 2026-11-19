#!/usr/bin/env python3
"""Explicit, guarded manual publish of a previously rendered live policy directory.

Default: read-only verification, no writes. Pass --publish --confirm-page-id 2194
to explicitly publish after reviewing the local preview.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from policies_composer.interact import InteractClient
from policies_composer.page_target import target_id, verify_page
from policies_composer.publish_guard import verified_artifact, build_update_payload


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output")
    parser.add_argument("--publish", action="store_true", help="Update the existing Interact page")
    parser.add_argument("--confirm-page-id", type=int, help="Must equal 2194 with --publish")
    args = parser.parse_args(argv)

    if args.publish and args.confirm_page_id != 2194:
        parser.error("--publish requires --confirm-page-id 2194")
    if not args.publish and args.confirm_page_id is not None:
        parser.error("--confirm-page-id requires --publish")

    html, count, digest = verified_artifact(args.output_dir)
    page_id = target_id()
    client = InteractClient()
    current = client.get_page(page_id)
    verified = verify_page(current, expected_id=page_id)
    payload = build_update_payload(current, html, count)

    if not args.publish:
        print(json.dumps({
            "mode": "DRY RUN - NO WRITE",
            "target": verified,
            "policy_count": count,
            "sha256": digest,
            "html_bytes": len(html.encode("utf-8")),
            "ready_for_manual_review": True,
        }, indent=2))
        return 0

    result = client.update_html_page(page_id, payload)
    print(json.dumps({
        "status": "publish request acknowledged",
        "target_content_id": page_id,
        "policy_count": count,
        "sha256": digest,
        "interact_response": result,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
