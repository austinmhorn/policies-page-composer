"""Normalize DB.Policies Notion pages to a stable directory model."""
from .models import Policy


def _text(items):
    return "".join(part.get("plain_text", "") for part in (items or [])).strip()


def _property_text(prop):
    if not isinstance(prop, dict):
        return ""
    kind = prop.get("type")
    if kind in ("title", "rich_text"):
        return _text(prop.get(kind))
    if kind in ("select", "status"):
        return (prop.get(kind) or {}).get("name") or ""
    if kind == "number":
        value = prop.get("number")
        return "" if value is None else str(value)
    if kind == "url":
        return prop.get("url") or ""
    if kind == "formula":
        formula = prop.get("formula") or {}
        return str(formula.get(formula.get("type")) or "")
    return ""


def normalize_page(page):
    props = page.get("properties", {})
    name = _property_text(props.get("Name", {}))
    number = _property_text(props.get("Number", {}))
    manual_prop = props.get("Manual", {})
    manual = _property_text(manual_prop)
    if not manual and manual_prop.get("type") == "multi_select":
        manual = ", ".join(x.get("name", "") for x in manual_prop.get("multi_select", []))
    link = _property_text(props.get("Deep Link", {}))
    kw_prop = props.get("Keywords", {})
    if kw_prop.get("type") == "multi_select":
        keywords = tuple(x.get("name", "").strip() for x in kw_prop.get("multi_select", []) if x.get("name"))
    else:
        keywords = tuple(x.strip() for x in _property_text(kw_prop).split(",") if x.strip())
    return Policy(name, number, manual, link, keywords, page.get("id", ""))
