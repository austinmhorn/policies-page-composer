import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from policies_composer import config
from policies_composer.interact import InteractClient


class ProjectEnvTests(unittest.TestCase):
    def test_project_env_overrides_stale_shell_values(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / ".env"
            path.write_text(
                'INTERACT_API_DOMAIN="https://interact.example.test"\n'
                'INTERACT_TENANT_GUID="tenant"\n'
                'INTERACT_API_KEY="api-key"\n'
                'INTERACT_API_SECRET="secret$with#special&characters"\n'
                'INTERACT_PERSON_ID="42"\n',
                encoding="utf-8",
            )
            with patch.object(config, "PROJECT_ENV", path):
                with patch.dict(os.environ, {"INTERACT_API_SECRET": "wrong-value"}):
                    client = InteractClient()
                    self.assertEqual(client.api_secret, "secret$with#special&characters")
                    self.assertEqual(client.person_id, 42)

    def test_missing_env_does_not_break_offline_work(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(config, "PROJECT_ENV", Path(temp) / "missing.env"):
                self.assertFalse(config.load_project_env())


if __name__ == "__main__":
    unittest.main()
