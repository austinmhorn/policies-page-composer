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

    def test_property_details_visual_contract_reused(self):
        fragment = render_directory(self.policies)
        self.assertIn("--policies-max-width:1440px", fragment)
        self.assertIn("Montserrat", fragment)
        self.assertIn("--policies-accent:#2cb1cc", fragment)
        self.assertIn("background:linear-gradient(135deg,#0a1929", fragment)
        self.assertIn("color-scheme:dark", fragment)
        self.assertIn("function expandPolicies(root)", fragment)
        self.assertIn("Math.min(1440", fragment)
        # Preserve the existing directory, searchable list, and manual filter.
        self.assertIn('data-policies-search', fragment)
        self.assertIn('data-policies-manual', fragment)
        self.assertIn('data-policy-record="true"', fragment)

    def test_interact_chrome_changes_are_pinned_to_page_2194(self):
        fragment = render_directory(self.policies)
        self.assertIn("get('id')==='2194'", fragment)
        self.assertIn("function hideNativePreviewMessage(root)", fragment)
        self.assertIn("function closePageDetailsPane()", fragment)
        self.assertIn("function hideDetailsPaneFallback(root)", fragment)
        self.assertIn("if(details)hideDetailsPaneFallback(root)", fragment)
        self.assertIn("body_btnBEPreview", fragment)
        self.assertNotIn("btnPrint", fragment)
        self.assertNotIn("body_btnPDF", fragment)

    def test_empty_directory_refused(self):
        with self.assertRaises(ValueError):
            render_directory([])
