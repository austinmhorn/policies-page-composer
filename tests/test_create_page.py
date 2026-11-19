import os
import unittest
from unittest.mock import Mock, patch

import requests

from policies_composer.interact import page_payload, InteractClient, InteractError
from scripts.create_page import main, initial_html, parse_ids


class CreatePageTests(unittest.TestCase):
    def test_plain_html_is_escaped_and_identified(self):
        html = initial_html("<Policies>")
        self.assertIn("&lt;Policies&gt;", html)
        self.assertIn('data-policies-page="true"', html)
        self.assertNotIn("<script", html)

    def test_payload_is_pure_html_and_not_public(self):
        p = page_payload(title="Policies", summary="Index", html="<div>ok</div>",
                         category_ids=[123], top_section_ids=[456], person_id=42)
        page = p["Page"]
        self.assertEqual(page["ContentType"], "html")
        self.assertFalse(page["IsBlockEditorPage"])
        self.assertFalse(page["IsPublic"])
        self.assertEqual(page["TopSectionIds"], [456])
        self.assertEqual(page["CategoryIds"], [123])
        self.assertEqual(p["Transition"]["State"], "Published")
        self.assertFalse(p["Transition"]["SendNotifications"])

    def test_dry_run_never_creates_page(self):
        with patch("scripts.create_page.InteractClient") as client:
            with patch("builtins.print"):
                status = main(["--category-ids", "123", "--top-section-ids", "456"])
            self.assertEqual(status, 0)
            client.assert_not_called()

    def test_live_requires_confirmation(self):
        with self.assertRaises(SystemExit):
            with patch("scripts.create_page.InteractClient") as client:
                main(["--category-ids", "123", "--top-section-ids", "456", "--create"])
                client.assert_not_called()

    def test_live_calls_client_once_with_confirmed_payload(self):
        with patch("scripts.create_page.InteractClient") as client:
            client.return_value.person_id = 42
            client.return_value.create_html_page.return_value = {"Id": 9999}
            with patch("builtins.print"):
                status = main([
                    "--category-ids", "123", "--top-section-ids", "456",
                    "--create", "--confirm-title", "Birchstone Policy Library",
                ])
            self.assertEqual(status, 0)
            client.return_value.create_html_page.assert_called_once()
            payload = client.return_value.create_html_page.call_args.args[0]
            self.assertEqual(payload["Page"]["AuthorId"], 42)

    def test_parse_ids_rejects_non_numeric(self):
        from argparse import ArgumentTypeError
        with self.assertRaises(ArgumentTypeError):
            parse_ids("123,abc")

    def make_client(self):
        env = {
            "INTERACT_API_DOMAIN": "https://interact.example.test",
            "INTERACT_TENANT_GUID": "tenant",
            "INTERACT_API_KEY": "key",
            "INTERACT_API_SECRET": "secret",
            "INTERACT_PERSON_ID": "42",
        }
        with patch.dict(os.environ, env):
            return InteractClient()

    def test_requests_auth_matches_property_composer(self):
        client = self.make_client()
        response = Mock()
        response.json.return_value = {"access_token": "token"}
        client.session.post = Mock(return_value=response)
        self.assertEqual(client.authenticate(), "token")
        args, kwargs = client.session.post.call_args
        self.assertEqual(args[0], "https://interact.example.test/token")
        self.assertEqual(kwargs["params"], {"personid": 42})
        self.assertEqual(kwargs["data"], {
            "grant_type": "authorization_code",
            "code": "key__secret",
            "context": "KeySecret",
        })
        self.assertEqual(kwargs["headers"]["X-Tenant"], "tenant")

    def test_create_uses_requests_and_bearer_token(self):
        client = self.make_client()
        response1 = Mock()
        response1.json.return_value = {"access_token": "token"}
        response2 = Mock()
        response2.json.return_value = {"Id": 9999}
        client.session.post = Mock(side_effect=[response1, response2])
        self.assertEqual(client.create_html_page({"Page": {"Title": "Policies"}}), {"Id": 9999})
        self.assertEqual(client.session.post.call_count, 2)
        args, kwargs = client.session.post.call_args
        self.assertEqual(args[0], "https://interact.example.test/api/page/composer")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer token")
        self.assertEqual(kwargs["json"]["Page"]["Title"], "Policies")

    def test_auth_http_error_does_not_leak_response(self):
        client = self.make_client()
        response = requests.Response()
        response.status_code = 400
        response._content = b'{"error":"sensitive server response"}'
        client.session.post = Mock(return_value=response)
        with self.assertRaisesRegex(InteractError, "HTTP 400") as captured:
            client.authenticate()
        self.assertNotIn("sensitive", str(captured.exception))


if __name__ == "__main__":
    unittest.main()
