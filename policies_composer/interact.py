"""Interact client modeled on the working Property Details Composer requests client.

This module handles one-time page creation only. It does not update existing pages.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from .config import load_project_env


class InteractError(RuntimeError):
    """Operational error that does not echo credentials or response bodies."""


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise InteractError(f"Missing required environment variable: {name}")
    return value


def page_payload(*, title: str, summary: str, html: str,
                 category_ids: list[int], top_section_ids: list[int],
                 person_id: int, keywords: list[str] | None = None) -> dict:
    """Build a pure-HTML Interact composer payload."""
    if not title.strip() or not html.strip():
        raise ValueError("Title and HTML content must not be blank.")
    if not category_ids or not top_section_ids:
        raise ValueError("Category and top section IDs must be explicitly configured.")
    if not all(isinstance(n, int) and n > 0 for n in category_ids + top_section_ids):
        raise ValueError("Category and top section IDs must be positive integers.")
    if person_id <= 0:
        raise ValueError("Interact person ID must be positive.")
    now = datetime.now(timezone.utc)
    return {
        "Transition": {
            "State": "Published",
            "Message": "Initial Policies Page Composer HTML page creation",
            "SendNotifications": False,
            "ResendMentions": False,
        },
        "Page": {
            "AuthorId": person_id,
            "PublishAsId": person_id,
            "PublisherType": 0,
            "CategoryIds": category_ids,
            "TopSectionIds": top_section_ids,
            "TagIds": [],
            "Keywords": keywords or ["policies", "procedures", "policy library"],
            "ContentType": "html",
            "Title": title.strip(),
            "Summary": summary.strip(),
            "Content": {"Html": html},
            "Features": {
                "DefaultToFullWidth": True,
                "AllowComments": False,
                "IsKeyPage": False,
                "Recommends": {"Show": False, "MaxContentAge": 7},
                "IsMandatoryRead": False,
                "ShowTimeToRead": False,
                "ShowPublishedDate": False,
                "ShowUpdatedDate": False,
            },
            "Audience": {"RelatedContent": [], "NotificationRecipients": []},
            "PubStartDate": now.isoformat(),
            "PubEndDate": (now + timedelta(days=3650)).isoformat(),
            "ReviewDate": (now + timedelta(days=365)).isoformat(),
            "IsPublic": False,
            "IsDiscoverable": True,
            "IsBlockEditorPage": False,
        },
    }


class InteractClient:
    def __init__(self) -> None:
        load_project_env()
        self.api_domain = required_env("INTERACT_API_DOMAIN").rstrip("/")
        if not self.api_domain.startswith("https://"):
            raise InteractError("INTERACT_API_DOMAIN must use HTTPS.")
        self.tenant_guid = required_env("INTERACT_TENANT_GUID")
        self.api_key = required_env("INTERACT_API_KEY")
        self.api_secret = required_env("INTERACT_API_SECRET")
        try:
            self.person_id = int(required_env("INTERACT_PERSON_ID"))
        except ValueError as exc:
            raise InteractError("INTERACT_PERSON_ID must be an integer.") from exc
        if self.person_id <= 0:
            raise InteractError("INTERACT_PERSON_ID must be positive.")
        self.session = requests.Session()
        self._token: str | None = None

    def authenticate(self) -> str:
        # Mirror Property Details Composer's working token request exactly.
        try:
            response = self.session.post(
                f"{self.api_domain}/token",
                params={"personid": self.person_id},
                headers={
                    "X-Tenant": self.tenant_guid,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "authorization_code",
                    "code": f"{self.api_key}__{self.api_secret}",
                    "context": "KeySecret",
                },
                timeout=30,
            )
            response.raise_for_status()
            token = response.json().get("access_token")
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            raise InteractError(f"Interact token request returned HTTP {status}.") from None
        except requests.RequestException:
            raise InteractError("Interact token request failed to connect.") from None
        except (ValueError, AttributeError):
            raise InteractError("Interact token response was not valid JSON.") from None
        if not isinstance(token, str) or not token:
            raise InteractError("Interact token response did not include access_token.")
        self._token = token
        return token

    def get_page(self, page_id: int) -> dict[str, Any]:
        """Read latest Page Composer metadata without changing the page."""
        if page_id != 2194:
            raise InteractError("Read-only verification only supports Policies page 2194.")
        token = self._token or self.authenticate()
        try:
            response = self.session.get(
                f"{self.api_domain}/api/page/{page_id}/composer/latest",
                headers={
                    "X-Tenant": self.tenant_guid,
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            raise InteractError(f"Interact page lookup returned HTTP {status}.") from None
        except requests.RequestException:
            raise InteractError("Interact page lookup failed to connect.") from None
        except ValueError:
            raise InteractError("Interact page lookup returned invalid JSON.") from None
        if not isinstance(result, dict):
            raise InteractError("Interact page lookup returned a non-object JSON response.")
        return result

    def create_html_page(self, payload: dict[str, Any]) -> dict[str, Any]:
        token = self._token or self.authenticate()
        try:
            response = self.session.post(
                f"{self.api_domain}/api/page/composer",
                headers={
                    "X-Tenant": self.tenant_guid,
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            raise InteractError(f"Interact page creation returned HTTP {status}.") from None
        except requests.RequestException:
            raise InteractError("Interact page creation request failed to connect.") from None
        except ValueError:
            raise InteractError("Interact page creation returned invalid JSON.") from None
        if not isinstance(result, dict):
            raise InteractError("Interact page creation returned a non-object JSON response.")
        return result

    def update_html_page(self, page_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """Update only the pinned Policies target with a separately verified payload."""
        if page_id != 2194:
            raise InteractError("Updates only support Policies page 2194.")
        if payload.get("Page", {}).get("ContentType") != "html":
            raise InteractError("Publishing requires an HTML page payload.")
        token = self._token or self.authenticate()
        try:
            response = self.session.put(
                f"{self.api_domain}/api/page/{page_id}/composer",
                headers={
                    "X-Tenant": self.tenant_guid,
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            raise InteractError(f"Interact page update returned HTTP {status}.") from None
        except requests.RequestException:
            raise InteractError("Interact page update request failed to connect.") from None
        except ValueError:
            raise InteractError("Interact page update returned invalid JSON.") from None
        if not isinstance(result, dict):
            raise InteractError("Interact page update returned a non-object JSON response.")
        return result
