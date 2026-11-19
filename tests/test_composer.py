import unittest

from policies_composer.models import Policy
from policies_composer.render import render_directory
from policies_composer.transform import normalize_page
from policies_composer.validate import ValidationError, validate_policies


URL = "https://performancehq.gracehill.com/auth/policy_deep_link_redirect?manual_id=9663&policy_id=540939&subdomain=birchstone"


class ComposerTests(unittest.TestCase):
    def example(self, **changes):
        data = dict(
            title="Customer Relations", number="100",
            manual="Leasing & Marketing", deep_link=URL
        )
        data.update(changes)
        return Policy(**data)

    def test_valid_policy(self):
        validate_policies([self.example()])

    def test_empty_input_rejected(self):
        with self.assertRaises(ValidationError):
            validate_policies([])

    def test_duplicate_link_rejected(self):
        with self.assertRaises(ValidationError):
            validate_policies([self.example(), self.example(number="105")])

    def test_wrong_host_rejected(self):
        with self.assertRaises(ValidationError):
            validate_policies([self.example(deep_link=URL.replace("gracehill.com", "example.com"))])

    def test_html_escapes_user_content(self):
        html = render_directory([self.example(title="<img src=x onerror=alert(1)>")])
        self.assertNotIn("<img src=x", html)
        self.assertIn("&lt;img", html)

    def test_normalize_notion_properties(self):
        p = normalize_page({"id": "abc", "properties": {
            "Name": {"type": "title", "title": [{"plain_text": "Customer Relations"}]},
            "Number": {"type": "rich_text", "rich_text": [{"plain_text": "100"}]},
            "Manual": {"type": "select", "select": {"name": "Leasing & Marketing"}},
            "Deep Link": {"type": "url", "url": URL},
            "Keywords": {"type": "multi_select", "multi_select": [{"name": "service"}]}
        }})
        self.assertEqual(p.keywords, ("service",))
        self.assertEqual(p.deep_link, URL)


if __name__ == "__main__":
    unittest.main()
