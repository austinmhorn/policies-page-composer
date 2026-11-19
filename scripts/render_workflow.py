#!/usr/bin/env python3
"""Read-only Notion -> validated snapshot -> standalone preview and HTML fragment."""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from policies_composer.notion import fetch_pages
from policies_composer.transform import normalize_page
from policies_composer.render import render_directory
from policies_composer.validate import validate_policies


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, help="Local Notion results JSON; bypass API")
    parser.add_argument("--minimum-count", type=int, default=int(os.getenv("POLICIES_MIN_COUNT", "1")))
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output")
    args = parser.parse_args()
    if args.minimum_count < 1:
        parser.error("--minimum-count must be at least 1")

    if args.fixture:
        payload = json.loads(args.fixture.read_text(encoding="utf-8"))
        pages = payload.get("results", payload) if isinstance(payload, dict) else payload
    else:
        pages = fetch_pages()

    policies = [normalize_page(p) for p in pages if not p.get("archived") and not p.get("in_trash")]
    validate_policies(policies, minimum_count=args.minimum_count)
    html = render_directory(policies)
    digest = hashlib.sha256(html.encode("utf-8")).hexdigest()
    timestamp = datetime.now(timezone.utc).isoformat()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    # Validation succeeds before replacing any saved output.
    (args.output_dir / "policies.fragment.html").write_text(html, encoding="utf-8")
    (args.output_dir / "policies.preview.html").write_text(html, encoding="utf-8")
    (args.output_dir / "render_manifest.json").write_text(json.dumps({
        "created_at": timestamp, "policy_count": len(policies),
        "sha256": digest, "source": "fixture" if args.fixture else "notion",
        "publish_authorized": False
    }, indent=2), encoding="utf-8")

    print(f"Rendered {len(policies)} policies; sha256={digest}")
    print(f"Preview: {args.output_dir / 'policies.preview.html'}")
    print("Publishing remains disabled in this foundation version.")


if __name__ == "__main__":
    main()
