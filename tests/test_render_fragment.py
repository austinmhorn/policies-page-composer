import unittest
from policies_composer.models import Policy
from policies_composer.render import render_directory, render_preview_document


class RenderSafetyTests(unittest.TestCase):
    def setUp(self):
        self.policies = [Policy(
            title="Visitor <script>alert(1)</script>",
            number="1.10 Entrata", manual="Customer Relations",
            deep_link="https://performancehq.gracehill.com/auth/policy_deep_link_redirect?manual_id=9663&policy_id=540939&subdomain=birchstone",
            keywords=("visitor",),
        )]

    def test_fragment_has_no_document_shell_and_escapes_policy(self):
        fragment = render_directory(self.policies)
        self.assertNotIn("<!doctype", fragment.lower())
        self.assertNotIn("<html", fragment.lower())
        self.assertNotIn("<body", fragment.lower())
        self.assertIn('data-policies-page="true"', fragment)
        self.assertIn('data-policy-record="true"', fragment)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", fragment)
        self.assertNotIn("body{", fragment)
        self.assertNotIn(":root{", fragment)

    def test_preview_wraps_publish_fragment_without_changing_it(self):
        fragment = render_directory(self.policies)
        preview = render_preview_document(fragment)
        self.assertIn("<!doctype html>", preview)
        self.assertIn(fragment, preview)

    def test_empty_directory_refused(self):
        with self.assertRaises(ValueError):
            render_directory([])
