"""Minimal Interact page-creation client following Property Details Composer's API contract.

Creation is a separate operator action. Rendering and scheduling never call this.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class InteractError(RuntimeError):
    """Safe operational error; never includes API keys or secrets."""


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise InteractError(f"Missing required environment variable: {name}")
    return value


def page_payload(*, title: str, summary: str, html: str,
                 category_ids: list[int], top_section_ids: list[int],
                 person_id: int, keywords: list[str] | None = None) -> dict:
    """Build the same pure-HTML composer payload as Property Details Composer."""
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
        self.domain = required_env("INTERACT_API_DOMAIN").rstrip("/")
        if not self.domain.startswith("https://"):
            raise InteractError("INTERACT_API_DOMAIN must use HTTPS.")
        self.tenant = required_env("INTERACT_TENANT_GUID")
        self.key = required_env("INTERACT_API_KEY")
        self.secret = required_env("INTERACT_API_SECRET")
        try:
            self.person_id = int(required_env("INTERACT_PERSON_ID"))
        except ValueError as exc:
            raise InteractError("INTERACT_PERSON_ID must be an integer.") from exc
        if self.person_id <= 0:
            raise InteractError("INTERACT_PERSON_ID must be positive.")

    def _send(self, request: Request) -> dict:
        try:
            with urlopen(request, timeout=30) as response:
                data = json.load(response)
        except HTTPError as exc:
            raise InteractError(f"Interact returned HTTP {exc.code}.") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise InteractError("Could not connect to Interact.") from exc
        except (ValueError, UnicodeError) as exc:
            raise InteractError("Interact returned an invalid JSON response.") from exc
        if not isinstance(data, dict):
            raise InteractError("Interact returned a non-object JSON response.")
        return data

    def authenticate(self) -> str:
        form = urlencode({
            "grant_type": "authorization_code",
            "code": f"{self.key}__{self.secret}",
            "context": "KeySecret",
        }).encode("utf-8")
        request = Request(
            f"{self.domain}/token?{urlencode({'personid': self.person_id})}",
            data=form,
            headers={
                "X-Tenant": self.tenant,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        token = self._send(request).get("access_token")
        if not isinstance(token, str) or not token:
            raise InteractError("Interact token response was missing access_token.")
        return token

    def create_html_page(self, payload: dict) -> dict:
        token = self.authenticate()
        request = Request(
            f"{self.domain}/api/page/composer",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "X-Tenant": self.tenant,
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        return self._send(request)
