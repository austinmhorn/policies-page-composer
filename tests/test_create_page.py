import os
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs

from policies_composer.interact import page_payload, InteractClient
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

    def test_real_client_authenticates_before_create(self):
        env = {
            "INTERACT_API_DOMAIN": "https://interact.example.test",
            "INTERACT_TENANT_GUID": "tenant",
            "INTERACT_API_KEY": "key",
            "INTERACT_API_SECRET": "secret",
            "INTERACT_PERSON_ID": "42",
        }
        with patch.dict(os.environ, env):
            client = InteractClient()
        with patch.object(client, "_send", side_effect=[
            {"access_token": "token"}, {"Id": 9999}
        ]) as sender:
            result = client.create_html_page({"Page": {"Title": "Policies"}})
            self.assertEqual(result["Id"], 9999)
            self.assertEqual(sender.call_count, 2)
            token_request = sender.call_args_list[0].args[0]
            create_request = sender.call_args_list[1].args[0]
            self.assertEqual(token_request.full_url,
                             "https://interact.example.test/token?personid=42")
            self.assertEqual(create_request.get_method(), "POST")
            self.assertEqual(create_request.full_url,
                             "https://interact.example.test/api/page/composer")
            self.assertEqual(create_request.get_header("Authorization"), "Bearer token")


if __name__ == "__main__":
    unittest.main()
