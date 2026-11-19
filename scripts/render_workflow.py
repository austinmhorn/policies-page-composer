#!/usr/bin/env python3
"""Go Notion fetch -> normalized JSON -> Python validation and static HTML preview."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from policies_composer.models import Policy
from policies_composer.transform import normalize_page
from policies_composer.render import render_directory, render_preview_document
from policies_composer.validate import validate_policies


def load_policies(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("policies")
    if not isinstance(records, list):
        raise ValueError("Go snapshot must contain a policies array")
    policies = []
    for i, record in enumerate(records, 1):
        if not isinstance(record, dict):
            raise ValueError(f"Policy record {i} is not an object")
        keywords = record.get("keywords") or []
        if not isinstance(keywords, list) or any(not isinstance(k, str) for k in keywords):
            raise ValueError(f"Policy record {i} has invalid keywords")
        policies.append(Policy(
            title=record.get("title", ""),
            number=record.get("number", ""),
            manual=record.get("manual", ""),
            deep_link=record.get("deep_link", ""),
            keywords=tuple(keywords),
            notion_page_id=record.get("notion_page_id", ""),
        ))
    return policies


def main():
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--fixture", type=Path, help="Test fixture containing raw Notion pages; skips Go")
    source.add_argument("--policies-json", type=Path, help="Use an existing Go-generated JSON snapshot")
    parser.add_argument("--minimum-count", type=int, default=int(os.getenv("POLICIES_MIN_COUNT", "1")))
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output")
    args = parser.parse_args()
    if args.minimum_count < 1:
        parser.error("--minimum-count must be at least 1")

    if args.fixture:
        payload = json.loads(args.fixture.read_text(encoding="utf-8"))
        pages = payload.get("results", payload) if isinstance(payload, dict) else payload
        policies = [normalize_page(p) for p in pages if not p.get("archived") and not p.get("in_trash")]
        source_label = "fixture"
    else:
        snapshot = args.policies_json or (ROOT / "data" / "policies.json")
        if not args.policies_json:
            subprocess.run(
                ["go", "run", "./cmd/policies-fetch", "--output", str(snapshot)],
                cwd=ROOT, check=True,
            )
        policies = load_policies(snapshot)
        source_label = "go-snapshot" if args.policies_json else "go-notion"

    validate_policies(policies, minimum_count=args.minimum_count)
    html = render_directory(policies)
    digest = hashlib.sha256(html.encode("utf-8")).hexdigest()
    timestamp = datetime.now(timezone.utc).isoformat()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    # Validation completes before any output is replaced.
    (args.output_dir / "policies.fragment.html").write_text(html, encoding="utf-8")
    (args.output_dir / "policies.preview.html").write_text(render_preview_document(html), encoding="utf-8")
    (args.output_dir / "render_manifest.json").write_text(json.dumps({
        "created_at": timestamp, "policy_count": len(policies),
        "sha256": digest, "source": source_label,
        "publish_authorized": False
    }, indent=2), encoding="utf-8")

    print(f"Rendered {len(policies)} policies; sha256={digest}")
    print(f"Preview: {args.output_dir / 'policies.preview.html'}")
    print("Publishing remains disabled.")


if __name__ == "__main__":
    main()
