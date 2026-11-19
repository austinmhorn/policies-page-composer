import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from policies_composer.page_target import target_id, verify_page
from scripts.verify_interact_page import main


class TargetTests(unittest.TestCase):
    def test_configuration_pins_2194(self):
        self.assertEqual(target_id(), 2194)

    def test_reject_wrong_target(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            path.write_text(json.dumps({
                "project": "policies-page-composer", "publishing_enabled": False,
                "interact_content_id": 2186,
                "property_details_content_id_excluded": 2186
            }))
            with self.assertRaises(RuntimeError):
                target_id(path)

    def test_accept_verified_target(self):
        result = verify_page({"ContentId": 2194, "Title": "Birchstone Policy Library",
                              "ContentType": "html", "IsBlockEditorPage": False})
        self.assertTrue(result["verified"])

    def test_missing_id_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "omitted"):
            verify_page({"Title": "Birchstone Policy Library", "ContentType": "html",
                         "IsBlockEditorPage": False})

    def test_block_editor_fails(self):
        with self.assertRaisesRegex(RuntimeError, "pure-HTML"):
            verify_page({"ContentId": 2194, "Title": "Birchstone Policy Library",
                         "ContentType": "html", "IsBlockEditorPage": True})

    def test_read_only_verification(self):
        with patch("scripts.verify_interact_page.InteractClient") as client:
            client.return_value.get_page.return_value = {
                "ContentId": 2194, "Title": "Birchstone Policy Library",
                "ContentType": "html", "IsBlockEditorPage": False
            }
            with patch("builtins.print"):
                main()
            client.return_value.get_page.assert_called_once_with(2194)
            client.return_value.create_html_page.assert_not_called()
