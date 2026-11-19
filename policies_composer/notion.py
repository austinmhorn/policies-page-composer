"""Read-only paginated Notion data-source or legacy database extraction."""
import json
import os
import urllib.error
import urllib.request


class NotionError(RuntimeError):
    pass


def fetch_pages(*, token=None, database_id=None, data_source_id=None, api_version=None):
    token = token or os.getenv("NOTION_TOKEN")
    database_id = database_id or os.getenv("NOTION_DATABASE_ID")
    data_source_id = data_source_id or os.getenv("NOTION_DATA_SOURCE_ID")
    api_version = api_version or os.getenv("NOTION_API_VERSION") or (
        "2025-09-03" if data_source_id else "2022-06-28"
    )
    if not token:
        raise NotionError("Set NOTION_TOKEN in the environment.")
    if not (data_source_id or database_id):
        raise NotionError("Set NOTION_DATA_SOURCE_ID or NOTION_DATABASE_ID.")
    endpoint = (
        f"https://api.notion.com/v1/data_sources/{data_source_id}/query"
        if data_source_id
        else f"https://api.notion.com/v1/databases/{database_id}/query"
    )
    cursor = None
    seen = set()
    result = []
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": api_version,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as error:
            raise NotionError(f"Notion returned HTTP {error.code} during query") from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise NotionError("Could not contact Notion API") from error
        batch = payload.get("results")
        if not isinstance(batch, list):
            raise NotionError("Notion response lacked a results array")
        result.extend(batch)
        if not payload.get("has_more"):
            break
        next_cursor = payload.get("next_cursor")
        if not next_cursor or next_cursor in seen:
            raise NotionError("Notion returned an invalid or repeated pagination cursor")
        seen.add(next_cursor)
        cursor = next_cursor
    return result
