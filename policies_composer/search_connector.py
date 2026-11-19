"""One-record Workplace Search connector test (connector app ID 2).

No bulk indexing, no sync sessions, and no user provisioning.
"""
import os
from urllib.parse import urlparse

import requests

from .models import Policy
from .validate import validate_policies

CONNECTOR_APP_ID = 2
API_PATH = "/api/search/connector/2/docs/addupdate"


def document_for_policy(policy: Policy, *, external_identity: str) -> dict:
    """Build a permission-scoped search document from validated Notion data."""
    validate_policies([policy])
    if not policy.notion_page_id or not isinstance(policy.notion_page_id, str):
        raise ValueError("A stable Notion page ID is required")
    identity = external_identity.strip()
    if not identity or len(identity) > 256:
        raise ValueError("A confirmed, nonempty Interact external identity is required")
    return {
        "GloballyUniqueId": "birchstone-policy:" + policy.notion_page_id,
        "DocTypeName": "Birchstone Policy",
        "Title": policy.title,
        "Url": policy.deep_link,
        "Summary": f"Birchstone policy {policy.number} · {policy.manual}. Opens in Grace Hill.",
        "Keywords": " ".join((policy.number, policy.manual, *policy.keywords)),
        "Taxonomy": [
            {"Name": "Manual", "Type": "Text", "TextValue": policy.manual},
            {"Name": "Policy Number", "Type": "Text", "TextValue": policy.number},
        ],
        "IsPublic": False,
        "ExternalIdentities": [identity],
        "DeletionMode": "Manual",
    }


def upload_one(document: dict) -> dict:
    """Explicitly upsert exactly one permission-scoped record."""
    if document.get("IsPublic") is not False:
        raise ValueError("Search record must remain nonpublic")
    identities = document.get("ExternalIdentities")
    if not isinstance(identities, list) or len(identities) != 1 or not identities[0]:
        raise ValueError("One confirmed external identity is required")
    api_key = os.environ.get("POLICIES_SEARCH_SECRET_KEY", "")
    tenant = os.environ.get("INTERACT_TENANT_GUID", "")
    domain = os.environ.get("INTERACT_API_DOMAIN", "")
    if not api_key or not tenant:
        raise ValueError("Missing connector secret or tenant GUID in project .env")
    parsed = urlparse(domain)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Interact API domain must be a valid HTTPS origin")
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise ValueError("Interact API domain must be an HTTPS origin without a path")
    try:
        response = requests.put(
            domain.rstrip("/") + API_PATH,
            headers={
                "X-ApiKey": api_key,
                "X-Tenant": tenant,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json=[document],
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        raise RuntimeError(f"Search connector returned HTTP {status}") from None
    except requests.RequestException:
        raise RuntimeError("Search connector request failed") from None
    except ValueError:
        raise RuntimeError("Search connector returned invalid JSON") from None
    if not isinstance(result, dict):
        raise RuntimeError("Unexpected connector response")
    expected = document["GloballyUniqueId"]
    if result.get("HasErrors") or result.get("Errors") or expected not in result.get("AddedUpdated", []):
        raise RuntimeError("Connector did not acknowledge the expected record; inspect connector logs")
    return {"acknowledged": True, "globally_unique_id": expected, "app_id": CONNECTOR_APP_ID}
