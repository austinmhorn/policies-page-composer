import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from policies_composer.models import Policy
from policies_composer.search_connector import (
    API_PATH, CONNECTOR_APP_ID, TEST_EMAIL, TEST_IDENTITY, TEST_USER_GID,
    USER_API_PATH, document_for_policy, upload_one, user_record_for_test, sync_test_user, get_document_state, _safe_error_diagnostic,
)
from scripts.sync_test_identity import main as user_sync_main
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

    def test_minimal_document_omits_optional_taxonomy(self):
        doc = document_for_policy(self.policy, external_identity=TEST_IDENTITY)
        self.assertNotIn("Taxonomy", doc)
        self.assertEqual(doc["DeletionMode"], "Explicit")
        self.assertFalse(doc["IsPublic"])

    def test_read_only_state_checks_doc_exists_without_write(self):
        response = Mock()
        response.json.return_value = {"DocExists": False, "DateLastUpdated": None}
        with patch.dict(os.environ, {
            "POLICIES_SEARCH_SECRET_KEY": "private",
            "INTERACT_TENANT_GUID": "tenant",
            "INTERACT_API_DOMAIN": "https://interact.example.test",
        }), patch("policies_composer.search_connector.requests.get",
                 return_value=response) as get, \
             patch("policies_composer.search_connector.requests.put") as put:
            result = get_document_state("birchstone-policy:notion-test-123")
        self.assertFalse(result["doc_exists"])
        self.assertEqual(get.call_args.kwargs["params"], {
            "docId": "birchstone-policy:notion-test-123"
        })
        put.assert_not_called()

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

    def test_http_500_diagnostics_never_expose_server_body_or_credentials(self):
        response = Mock()
        response.status_code = 500
        response.headers = {
            "Content-Type": "application/json; charset=utf-8",
            "X-Request-ID": "safe-request-123",
        }
        response.content = b'{"Message":"Sensitive details: API_SECRET DO_NOT_SHARE"}'
        response.json.return_value = {
            "Message": "Sensitive details: API_SECRET DO_NOT_SHARE",
            "Errors": [{
                "Errors": [{"ErrorCode": 4, "ErrorMessage": "API_SECRET DO_NOT_SHARE"}]
            }],
        }
        diagnostic = _safe_error_diagnostic(response)
        self.assertEqual(diagnostic["http_status"], 500)
        self.assertEqual(diagnostic["error_codes"], [4])
        self.assertEqual(diagnostic["x-request-id"], "safe-request-123")
        self.assertNotIn("API_SECRET", str(diagnostic))
        self.assertNotIn("DO_NOT_SHARE", str(diagnostic))

    def test_user_record_is_allowlisted_and_explicit(self):
        record = user_record_for_test()
        self.assertEqual(record["Email"], TEST_EMAIL)
        self.assertEqual(record["GloballyUniqueId"], TEST_USER_GID)
        self.assertEqual(record["ExternalIdentities"], [TEST_IDENTITY])
        self.assertEqual(record["DeletionMode"], "Explicit")
        with self.assertRaises(ValueError):
            user_record_for_test(email="different@example.com")

    def test_user_sync_calls_documented_endpoint_and_checks_match(self):
        record = user_record_for_test()
        response = Mock()
        response.json.return_value = {
            "HasErrors": False, "Errors": [], "Added": [TEST_USER_GID],
            "Updated": [], "NotFound": [],
        }
        with patch.dict(os.environ, {
            "POLICIES_SEARCH_SECRET_KEY": "private",
            "INTERACT_TENANT_GUID": "tenant",
            "INTERACT_API_DOMAIN": "https://interact.example.test",
        }), patch("policies_composer.search_connector.requests.put",
                 return_value=response) as put:
            self.assertTrue(sync_test_user(record)["acknowledged"])
        args, kwargs = put.call_args
        self.assertEqual(args[0], "https://interact.example.test" + USER_API_PATH)
        self.assertEqual(kwargs["json"], [record])
        self.assertEqual(kwargs["headers"]["X-ApiKey"], "private")

    def test_user_sync_rejects_unmatched_account(self):
        response = Mock()
        response.json.return_value = {
            "HasErrors": False, "Errors": [], "Added": [],
            "Updated": [], "NotFound": [TEST_USER_GID],
        }
        with patch.dict(os.environ, {
            "POLICIES_SEARCH_SECRET_KEY": "private",
            "INTERACT_TENANT_GUID": "tenant",
            "INTERACT_API_DOMAIN": "https://interact.example.test",
        }), patch("policies_composer.search_connector.requests.put", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "did not confirm"):
                sync_test_user(user_record_for_test())

    def test_user_identity_cli_defaults_to_dry_run(self):
        with patch("scripts.sync_test_identity.sync_test_user") as sync, \
             patch("builtins.print"):
            self.assertEqual(user_sync_main([]), 0)
            sync.assert_not_called()
        with self.assertRaises(SystemExit):
            user_sync_main(["--write"])

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
