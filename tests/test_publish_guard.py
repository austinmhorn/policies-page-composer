import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from policies_composer.publish_guard import verified_artifact, build_update_payload
from policies_composer.models import Policy
from policies_composer.render import render_directory
from scripts.publish_policies import main


def current_page():
    return {
        "ContentId": 2194, "Title": "Birchstone Policy Library",
        "ContentType": "html", "IsBlockEditorPage": False,
        "Author": {"Id": 42}, "PublishedAs": {"Id": 42, "PublisherType": 0},
        "AssetId": 99, "Categories": [{"Id": 3624}],
        "TopSectionIds": [3573], "Features": {"DefaultToFullWidth": True},
        "Tags": [], "Keywords": ["policies"],
    }


class PublishGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)
        self.html = '<div data-policies-page="true">' + (
            '<article data-policy-record="true"></article>' * 415
        ) + '</div>'
        self.manifest = {
            "source": "go-notion", "policy_count": 415,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "sha256": hashlib.sha256(self.html.encode()).hexdigest(),
            "publish_authorized": False,
        }
        self.write()

    def write(self):
        (self.out / "policies.fragment.html").write_text(self.html)
        (self.out / "render_manifest.json").write_text(json.dumps(self.manifest))

    def test_valid_live_artifact(self):
        html, count, _ = verified_artifact(self.out)
        self.assertEqual(html, self.html)
        self.assertEqual(count, 415)

    def test_actual_renderer_script_does_not_trigger_false_duplicate_root(self):
        policy = Policy(
            title="Emergency Procedure",
            number="5070",
            manual="Emergency Procedures",
            deep_link="https://performancehq.gracehill.com/auth/policy_deep_link_redirect?manual_id=9662&policy_id=540867&subdomain=birchstone",
            keywords=(),
        )
        self.html = render_directory([policy] * 415)
        self.manifest["sha256"] = hashlib.sha256(self.html.encode()).hexdigest()
        self.write()
        rendered, count, _ = verified_artifact(self.out)
        self.assertEqual(rendered, self.html)
        self.assertEqual(count, 415)

    def test_actual_duplicate_html_roots_rejected(self):
        self.html = self.html.replace(
            '<div data-policies-page="true">',
            '<div data-policies-page="true"><div data-policies-page="true">',
            1,
        )
        self.manifest["sha256"] = hashlib.sha256(self.html.encode()).hexdigest()
        self.write()
        with self.assertRaisesRegex(RuntimeError, "one isolated root"):
            verified_artifact(self.out)

    def test_rejects_fixture(self):
        self.manifest["source"] = "fixture"
        self.write()
        with self.assertRaisesRegex(RuntimeError, "live-Notion"):
            verified_artifact(self.out)

    def test_rejects_tampered_fragment(self):
        self.html += "tamper"
        self.write()
        with self.assertRaisesRegex(RuntimeError, "hash"):
            verified_artifact(self.out)

    def test_rejects_short_dataset(self):
        self.manifest["policy_count"] = 414
        self.write()
        with self.assertRaisesRegex(RuntimeError, "at least"):
            verified_artifact(self.out)

    def test_build_preserves_metadata(self):
        payload = build_update_payload(current_page(), self.html, 415)
        self.assertEqual(payload["Page"]["AssetId"], 99)
        self.assertEqual(payload["Page"]["Content"]["Html"], self.html)
        self.assertFalse(payload["Transition"]["SendNotifications"])

    def test_dry_run_never_puts(self):
        with patch("scripts.publish_policies.InteractClient") as client:
            client.return_value.get_page.return_value = current_page()
            with patch("builtins.print"):
                self.assertEqual(main(["--output-dir", str(self.out)]), 0)
            client.return_value.update_html_page.assert_not_called()

    def test_publish_requires_exact_confirmation(self):
        with self.assertRaises(SystemExit):
            main(["--output-dir", str(self.out), "--publish"])

    def test_explicit_publish(self):
        with patch("scripts.publish_policies.InteractClient") as client:
            client.return_value.get_page.return_value = current_page()
            client.return_value.update_html_page.return_value = {"Acknowledged": True}
            with patch("builtins.print"):
                self.assertEqual(main(["--output-dir", str(self.out),
                                       "--publish", "--confirm-page-id", "2194"]), 0)
            args = client.return_value.update_html_page.call_args.args
            self.assertEqual(args[0], 2194)
            self.assertEqual(args[1]["Page"]["Content"]["Html"], self.html)


if __name__ == "__main__":
    unittest.main()
