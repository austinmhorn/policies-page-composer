import tempfile
import json
import unittest
from pathlib import Path

from scripts.render_workflow import load_policies
from policies_composer.validate import validate_policies


class GoSnapshotTests(unittest.TestCase):
    def test_snapshot_converted_to_python_policy(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "policies.json"
            path.write_text(json.dumps({"policies": [{
                "title": "Customer Relations",
                "number": "100",
                "manual": "Leasing & Marketing",
                "deep_link": "https://performancehq.gracehill.com/auth/policy_deep_link_redirect?manual_id=9663&policy_id=540939&subdomain=birchstone",
                "keywords": ["service"],
                "notion_page_id": "abc"
            }]}), encoding="utf-8")
            policies = load_policies(path)
            self.assertEqual(policies[0].notion_page_id, "abc")
            validate_policies(policies)

    def test_invalid_snapshot_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "policies.json"
            path.write_text('{"policies":{}}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_policies(path)
