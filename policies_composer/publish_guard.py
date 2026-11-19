"""Fail-closed validation of a saved, live-Notion policy render."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .page_target import target_id

MIN_POLICIES = 415
MAX_RENDER_AGE_HOURS = 24


def verified_artifact(output_dir: Path):
    """Return the exact saved fragment only after validating its manifest."""
    path = Path(output_dir)
    manifest = json.loads((path / "render_manifest.json").read_text(encoding="utf-8"))
    html = (path / "policies.fragment.html").read_text(encoding="utf-8")

    if target_id() != 2194:
        raise RuntimeError("Unexpected Policies destination")
    if manifest.get("source") != "go-notion":
        raise RuntimeError("Only a freshly fetched, live-Notion render can be published")
    count = manifest.get("policy_count")
    if type(count) is not int or count < MIN_POLICIES:
        raise RuntimeError(f"Policies publish requires at least {MIN_POLICIES} records")
    stamp = datetime.fromisoformat(manifest["created_at"].replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise RuntimeError("Render timestamp must include timezone")
    age = datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)
    if age.total_seconds() < -60 or age.total_seconds() > MAX_RENDER_AGE_HOURS * 3600:
        raise RuntimeError("Render is stale or has a timestamp in the future")
    actual_hash = hashlib.sha256(html.encode("utf-8")).hexdigest()
    if actual_hash != manifest.get("sha256"):
        raise RuntimeError("Saved HTML hash does not match its render manifest")
    if html.count('data-policy-record="true"') != count:
        raise RuntimeError("Rendered policy count does not match the manifest")
    if html.count('data-policies-page="true"') != 1:
        raise RuntimeError("Policies fragment must contain one isolated root")
    if "<html" in html.lower() or "<!doctype" in html.lower() or "<body" in html.lower():
        raise RuntimeError("Cannot publish a standalone HTML document into Interact")
    if manifest.get("publish_authorized") is not False:
        raise RuntimeError("Unexpected manifest publication state")
    return html, count, actual_hash


def build_update_payload(current: dict, html: str, count: int) -> dict:
    """Preserve Interact page metadata using the proven Property Details contract."""
    if not isinstance(current.get("Author"), dict) or "Id" not in current["Author"]:
        raise RuntimeError("Missing Interact page author metadata")
    if not isinstance(current.get("PublishedAs"), dict) or "Id" not in current["PublishedAs"]:
        raise RuntimeError("Missing Interact published-as metadata")
    if "AssetId" not in current:
        raise RuntimeError("Missing Interact AssetId")
    categories = current.get("Categories")
    if not isinstance(categories, list) or not categories or not all(
        isinstance(item, dict) and "Id" in item for item in categories
    ):
        raise RuntimeError("Missing Interact category metadata")
    top_sections = current.get("TopSectionIds")
    if not isinstance(top_sections, list) or not top_sections:
        raise RuntimeError("Missing Interact top-section metadata")
    tags = [
        tag.get("TagId", tag.get("Id"))
        for tag in current.get("Tags", [])
        if isinstance(tag, dict) and tag.get("TagId", tag.get("Id")) is not None
    ]
    keywords = [
        k if isinstance(k, str) else (k.get("Value") or k.get("value"))
        for k in current.get("Keywords", []) if isinstance(k, (str, dict))
    ]
    page = {
        "AuthorId": current["Author"]["Id"],
        "PublishAsId": current["PublishedAs"]["Id"],
        "PublisherType": current["PublishedAs"].get("PublisherType", 0),
        "CategoryIds": [item["Id"] for item in categories],
        "TopSectionIds": top_sections,
        "AssetId": current["AssetId"],
        "TagIds": tags,
        "Keywords": [k for k in keywords if k],
        "ContentType": "html",
        "Title": current["Title"],
        "Summary": current.get("Summary", ""),
        "Content": {"Html": html},
        "Features": current.get("Features", {}),
        "Audience": current.get("Audience", {"RelatedContent": [], "NotificationRecipients": []}),
        "PubStartDate": current.get("PubStartDate"),
        "PubEndDate": current.get("PubEndDate"),
        "ReviewDate": current.get("ReviewDate"),
        "ConfidentialityId": current.get("ConfidentialityId"),
        "ClassificationId": current.get("ClassificationId"),
        "BestBets": current.get("BestBets", []),
        "IsPublic": current.get("IsPublic", False),
        "IsDiscoverable": current.get("IsDiscoverable", True),
        "HasPublicationDateBeenSet": current.get("HasPublicationDateBeenSet", False),
        "IsBlockEditorPage": False,
    }
    return {
        "Transition": {
            "State": "Published",
            "Message": f"Policies Page Composer manual publish: {count} verified policies",
            "SendNotifications": False,
            "ResendMentions": False,
        },
        "Page": {key: value for key, value in page.items() if value is not None},
    }
