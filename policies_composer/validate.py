"""Fail-closed validation before producing publishable HTML."""
from urllib.parse import parse_qs, urlparse


class ValidationError(ValueError):
    pass


def validate_policies(policies, *, minimum_count=1):
    if len(policies) < minimum_count:
        raise ValidationError(f"Only {len(policies)} policies; minimum is {minimum_count}")
    seen_links = set()
    seen_manual_numbers = set()
    for i, p in enumerate(policies, 1):
        if not p.title or not p.manual or not p.number or not p.deep_link:
            raise ValidationError(f"Policy record {i} is missing title, manual, number, or deep link")
        parsed = urlparse(p.deep_link)
        if parsed.scheme != "https" or parsed.hostname != "performancehq.gracehill.com":
            raise ValidationError(f"Invalid Grace Hill deep link on policy record {i}")
        if parsed.path != "/auth/policy_deep_link_redirect":
            raise ValidationError(f"Unexpected deep-link path on policy record {i}")
        q = parse_qs(parsed.query)
        if not all(len(q.get(k, [])) == 1 and q[k][0] for k in ("manual_id", "policy_id", "subdomain")):
            raise ValidationError(f"Incomplete deep link on policy record {i}")
        if not q["manual_id"][0].isdigit() or not q["policy_id"][0].isdigit() or q["subdomain"][0] != "birchstone":
            raise ValidationError(f"Unexpected deep-link identifiers on policy record {i}")
        link_key = (q["manual_id"][0], q["policy_id"][0])
        if link_key in seen_links:
            raise ValidationError(f"Duplicate Grace Hill policy link on record {i}")
        seen_links.add(link_key)
        name_key = (p.manual.casefold(), p.number.casefold())
        if name_key in seen_manual_numbers:
            raise ValidationError(f"Duplicate manual and policy number on record {i}")
        seen_manual_numbers.add(name_key)
