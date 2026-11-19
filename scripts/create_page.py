#!/usr/bin/env python3
"""Create the initial pure-HTML Interact Policies page.

Default is a no-network dry run. Real creation requires --create plus an exact
title confirmation. This script never updates or overwrites an existing page.
"""
import argparse
import json
import os
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from policies_composer.interact import InteractClient, page_payload

DEFAULT_TITLE = "Birchstone Policy Library"
DEFAULT_SUMMARY = "Searchable reference directory of Birchstone policies and procedures."


def parse_ids(raw: str) -> list[int]:
    try:
        ids = [int(piece.strip()) for piece in raw.split(",") if piece.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("IDs must be comma-separated positive integers") from exc
    if not ids or any(n <= 0 for n in ids):
        raise argparse.ArgumentTypeError("Provide one or more positive integer IDs")
    return ids


def initial_html(title: str) -> str:
    """Plain HTML shell—no styling, JS, policy records or Property Details assets."""
    return (
        '<div class="policies-page" data-policies-page="true">\n'
        f'  <h1>{escape(title)}</h1>\n'
        '  <p>Policy directory setup in progress.</p>\n'
        '</div>'
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", default=DEFAULT_TITLE)
    parser.add_argument("--summary", default=DEFAULT_SUMMARY)
    parser.add_argument("--category-ids", required=True, type=parse_ids,
                        help="Interact category IDs, comma-separated (do not reuse Property Details IDs without checking)")
    parser.add_argument("--top-section-ids", required=True, type=parse_ids,
                        help="Interact top section IDs, comma-separated")
    parser.add_argument("--person-id", type=int,
                        help="Author/publisher ID for dry-run; live creation uses INTERACT_PERSON_ID")
    parser.add_argument("--create", action="store_true",
                        help="Actually create the initial published page (default: dry run)")
    parser.add_argument("--confirm-title", default="",
                        help="Required with --create; must exactly match --title")
    parser.add_argument("--html-file", type=Path,
                        help="Optional reviewed HTML fragment instead of the initial shell")
    args = parser.parse_args(argv)

    if args.create and args.confirm_title != args.title:
        parser.error("--create requires --confirm-title exactly matching --title")

    if args.html_file:
        if not args.html_file.is_file():
            parser.error("HTML file does not exist")
        html = args.html_file.read_text(encoding="utf-8")
    else:
        html = initial_html(args.title)

    if args.create:
        client = InteractClient()
        if args.person_id is not None and args.person_id != client.person_id:
            parser.error("--person-id does not match INTERACT_PERSON_ID")
        person_id = client.person_id
    else:
        try:
            person_id = args.person_id or int(os.environ.get("INTERACT_PERSON_ID", "1"))
        except ValueError:
            parser.error("INTERACT_PERSON_ID must be an integer")

    payload = page_payload(
        title=args.title, summary=args.summary, html=html,
        category_ids=args.category_ids,
        top_section_ids=args.top_section_ids,
        person_id=person_id,
    )
    if not args.create:
        print("DRY RUN: No Interact API calls were made.")
        print(json.dumps(payload, indent=2))
        return 0

    result = client.create_html_page(payload)
    # The response format varies across Interact tenants: show response to operator
    # without writing it to source control or guessing a new page ID.
    print("Interact returned a successful page-creation response:")
    print(json.dumps(result, indent=2))
    print("Record the new Policies page ID and verify page type before enabling any publishing workflow.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
