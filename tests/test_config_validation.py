"""Ensure bad configuration values produce actionable failures."""
import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_isolated_config():
    spec = importlib.util.spec_from_file_location("jarvis_test_config", ROOT / "config.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ConfigValidationTests(unittest.TestCase):
    def test_bad_port_is_rejected_with_name(self):
        with patch.dict(os.environ, {"N8N_NOTIFY_PORT": "abc"}):
            with self.assertRaisesRegex(ValueError, "N8N_NOTIFY_PORT"):
                load_isolated_config()

    def test_invalid_port_range_is_rejected(self):
        with patch.dict(os.environ, {"SMTP_PORT": "65536"}):
            with self.assertRaisesRegex(ValueError, "SMTP_PORT"):
                load_isolated_config()

    def test_wake_model_can_be_configured(self):
        with patch.dict(os.environ, {"WAKE_MODEL_NAME": "hey jarvis"}):
            self.assertEqual(load_isolated_config().WAKE_MODEL_NAME, "hey jarvis")


if __name__ == "__main__":
    unittest.main()
