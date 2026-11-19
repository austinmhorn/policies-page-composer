"""Policies-only destination configuration and read-only page verification."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_FILE = ROOT / "config" / "interact_target.json"


def target_id(config_file: Path = CONFIG_FILE) -> int:
    config = json.loads(config_file.read_text(encoding="utf-8"))
    if config.get("project") != "policies-page-composer":
        raise RuntimeError("Target configuration belongs to another project.")
    if config.get("publishing_enabled") is not False:
        raise RuntimeError("Policies publishing must remain disabled in this phase.")
    page_id = config.get("interact_content_id")
    if type(page_id) is not int or page_id != 2194:
        raise RuntimeError("Unexpected Policies Interact content target.")
    if page_id == config.get("property_details_content_id_excluded"):
        raise RuntimeError("Target conflicts with Property Details.")
    return page_id


def verify_page(page: dict, *, expected_id: int = 2194) -> dict:
    """Fail closed on uncertain page identity, type, or ownership."""
    if not isinstance(page, dict):
        raise RuntimeError("Interact page response must be an object.")
    actual_id = page.get("ContentId", page.get("Id"))
    # Some latest composer payloads identify the content via AssetId only;
    # do not guess identity from it.
    if actual_id is None:
        raise RuntimeError("Interact page response omitted ContentId/Id; cannot verify identity.")
    if str(actual_id) != str(expected_id):
        raise RuntimeError("Interact page identity did not match the configured Policies target.")
    if page.get("IsBlockEditorPage") is not False:
        raise RuntimeError("Cannot confirm the target is a pure-HTML Page Composer page.")
    if page.get("ContentType", "").lower() != "html":
        raise RuntimeError("Interact target ContentType is not html.")
    if page.get("Title") != "Birchstone Policy Library":
        raise RuntimeError("Unexpected Interact page title; refusing to trust this target.")
    return {
        "content_id": expected_id,
        "title": page["Title"],
        "content_type": page["ContentType"],
        "is_block_editor_page": page["IsBlockEditorPage"],
        "verified": True,
    }
