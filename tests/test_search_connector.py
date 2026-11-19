import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from policies_composer.models import Policy
from policies_composer.search_connector import (
    API_PATH, CONNECTOR_APP_ID, document_for_policy, upload_one,
)
from scripts.search_connector_test import main


class ConnectorTests(unittest.TestCase):
    def setUp(self):
        self.policy = Policy(
            title="Emergency Eyewash",
            number="5067",
            manual="Emergency Procedures",
            deep_link="https://performancehq.gracehill.com/auth/policy_deep_link_redirect?manual_id=9662&policy_id=540880&subdomain=birchstone",
            notion_page_id="notion-test-123",
            keywords=("eyewash",),
        )

    def test_document_points_directly_to_grace_hill_and_is_restricted(self):
        doc = document_for_policy(self.policy, external_identity="test-identity")
        self.assertEqual(doc["GloballyUniqueId"], "birchstone-policy:notion-test-123")
        self.assertEqual(doc["Title"], "Emergency Eyewash")
        self.assertEqual(doc["Url"], self.policy.deep_link)
        self.assertFalse(doc["IsPublic"])
        self.assertEqual(doc["ExternalIdentities"], ["test-identity"])
        self.assertEqual(doc["DocTypeName"], "Birchstone Policy")

    def test_requires_external_identity(self):
        with self.assertRaisesRegex(ValueError, "confirmed"):
            document_for_policy(self.policy, external_identity="")

    def test_requires_stable_id(self):
        with self.assertRaisesRegex(ValueError, "stable"):
            document_for_policy(Policy(
                title=self.policy.title, number=self.policy.number,
                manual=self.policy.manual, deep_link=self.policy.deep_link,
            ), external_identity="test")

    def test_upload_calls_exact_endpoint_with_connector_secret(self):
        doc = document_for_policy(self.policy, external_identity="test-identity")
        response = Mock()
        response.json.return_value = {
            "HasErrors": False, "Errors": [], "AddedUpdated": [doc["GloballyUniqueId"]]
        }
        with patch.dict(os.environ, {
            "POLICIES_SEARCH_SECRET_KEY": "connector-private",
            "INTERACT_TENANT_GUID": "tenant",
            "INTERACT_API_DOMAIN": "https://interact.example.test",
        }), patch("policies_composer.search_connector.requests.put", return_value=response) as put:
            result = upload_one(doc)
        self.assertTrue(result["acknowledged"])
        args, kwargs = put.call_args
        self.assertEqual(args[0], "https://interact.example.test" + API_PATH)
        self.assertEqual(kwargs["headers"]["X-ApiKey"], "connector-private")
        self.assertEqual(kwargs["headers"]["X-Tenant"], "tenant")
        self.assertEqual(kwargs["json"], [doc])
        self.assertEqual(CONNECTOR_APP_ID, 2)

    def test_upload_fails_on_partial_errors(self):
        doc = document_for_policy(self.policy, external_identity="test-identity")
        response = Mock()
        response.json.return_value = {
            "HasErrors": True, "Errors": [{"GloballyUniqueId": doc["GloballyUniqueId"]}],
            "AddedUpdated": [],
        }
        with patch.dict(os.environ, {
            "POLICIES_SEARCH_SECRET_KEY": "connector-private",
            "INTERACT_TENANT_GUID": "tenant",
            "INTERACT_API_DOMAIN": "https://interact.example.test",
        }), patch("policies_composer.search_connector.requests.put", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "did not acknowledge"):
                upload_one(doc)

    def test_cli_write_requires_explicit_gate(self):
        with self.assertRaises(SystemExit):
            main(["--write"])

    def test_dry_run_never_calls_network(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policies.json"
            records = []
            for idx in range(415):
                records.append({
                    "title": "Emergency Eyewash" if idx == 0 else f"Policy {idx}",
                    "number": "5067" if idx == 0 else str(6000 + idx),
                    "manual": "Emergency Procedures",
                    "deep_link": "https://performancehq.gracehill.com/auth/policy_deep_link_redirect?"
                                 f"manual_id=9662&policy_id={540880 + idx}&subdomain=birchstone",
                    "notion_page_id": f"notion-{idx}",
                    "keywords": [],
                })
            path.write_text(json.dumps({"policies": records}))
            with patch("scripts.search_connector_test.load_project_env"), \
                 patch("scripts.search_connector_test.upload_one") as upload, \
                 patch("builtins.print"):
                self.assertEqual(main(["--snapshot", str(path)]), 0)
                upload.assert_not_called()


if __name__ == "__main__":
    unittest.main()
