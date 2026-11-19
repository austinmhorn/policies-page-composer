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
        # Keep initial indexing minimal. Taxonomy can be introduced only after
        # Interact accepts a one-document baseline without HTTP 500.
        "IsPublic": False,
        "ExternalIdentities": [identity],
        "DeletionMode": "Explicit",
    }


TEST_EMAIL = "austinhorn@birchstoneres.com"
TEST_IDENTITY = "birchstone-policies-test"
TEST_USER_GID = "birchstone-policies-test-user"
USER_API_PATH = "/api/search/connector/2/users/addupdate"


def user_record_for_test(*, email: str = TEST_EMAIL) -> dict:
    """Single confirmed Interact account; no user creation or bulk sync."""
    if email.casefold().strip() != TEST_EMAIL:
        raise ValueError("Test identity synchronization is pinned to the confirmed account")
    return {
        "Email": TEST_EMAIL,
        "GloballyUniqueId": TEST_USER_GID,
        "DeletionMode": "Explicit",
        "ExternalIdentities": [TEST_IDENTITY],
    }


def _connector_settings() -> tuple[str, dict]:
    key = os.environ.get("POLICIES_SEARCH_SECRET_KEY", "")
    tenant = os.environ.get("INTERACT_TENANT_GUID", "")
    domain = os.environ.get("INTERACT_API_DOMAIN", "")
    if not key or not tenant:
        raise ValueError("Missing connector secret or tenant GUID in project .env")
    parsed = urlparse(domain)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Interact API domain must be a valid HTTPS origin")
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise ValueError("Interact API domain must be an HTTPS origin without a path")
    return domain.rstrip("/"), {
        "X-ApiKey": key,
        "X-Tenant": tenant,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _send_connector_update(path: str, records: list[dict]) -> dict:
    domain, headers = _connector_settings()
    if len(records) != 1:
        raise ValueError("Only one record may be submitted during connector testing")
    try:
        response = requests.put(
            domain + path, headers=headers, json=records, timeout=30
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
    return result


def sync_test_user(record: dict) -> dict:
    """Upsert only the confirmed user's connector-scoped identity."""
    if record != user_record_for_test():
        raise ValueError("Only the confirmed test user identity is allowed")
    result = _send_connector_update(USER_API_PATH, [record])
    gid = TEST_USER_GID
    if (
        result.get("HasErrors")
        or result.get("Errors")
        or gid in result.get("NotFound", [])
        or gid not in (result.get("Added", []) + result.get("Updated", []))
    ):
        raise RuntimeError("Connector did not confirm the matched test user")
    return {"acknowledged": True, "test_user_matched": True,
            "identity": TEST_IDENTITY, "app_id": CONNECTOR_APP_ID}


def get_document_state(globally_unique_id: str) -> dict:
    """Read-only check after a failed write; avoids blind duplicate retries."""
    if not globally_unique_id.startswith("birchstone-policy:"):
        raise ValueError("Document state lookup only accepts policy IDs")
    domain, headers = _connector_settings()
    try:
        response = requests.get(
            domain + "/api/search/connector/2/docs/state",
            params={"docId": globally_unique_id},
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        state = response.json()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        raise RuntimeError(f"Document state lookup returned HTTP {status}") from None
    except requests.RequestException:
        raise RuntimeError("Document state lookup failed to connect") from None
    except ValueError:
        raise RuntimeError("Document state lookup returned invalid JSON") from None
    if not isinstance(state, dict) or not isinstance(state.get("DocExists"), bool):
        raise RuntimeError("Document state response lacks a valid DocExists value")
    return {"doc_exists": state["DocExists"], "app_id": CONNECTOR_APP_ID,
            "globally_unique_id": globally_unique_id}


def upload_one(document: dict) -> dict:
    """Explicitly upsert exactly one permission-scoped record."""
    if document.get("IsPublic") is not False:
        raise ValueError("Search record must remain nonpublic")
    identities = document.get("ExternalIdentities")
    if not isinstance(identities, list) or len(identities) != 1 or not identities[0]:
        raise ValueError("One confirmed external identity is required")
    result = _send_connector_update(API_PATH, [document])
    expected = document["GloballyUniqueId"]
    if result.get("HasErrors") or result.get("Errors") or expected not in result.get("AddedUpdated", []):
        raise RuntimeError("Connector did not acknowledge the expected record; inspect connector logs")
    return {"acknowledged": True, "globally_unique_id": expected, "app_id": CONNECTOR_APP_ID}
