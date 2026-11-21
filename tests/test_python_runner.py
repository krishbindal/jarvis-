"""Security regression tests for opt-in Python subprocesses."""
import os
import unittest
from unittest.mock import patch

from executor.python_runner import _child_environment, run_python_code


class PythonRunnerTests(unittest.TestCase):
    def test_disabled_by_default(self):
        with patch("config.ALLOW_CODE_EXECUTION", False):
            result = run_python_code("print('do not run')")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "disabled")

    def test_secrets_not_inherited(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "fake-key", "EMAIL_PASS": "fake-password"}):
            child = _child_environment()
            self.assertNotIn("GROQ_API_KEY", child)
            self.assertNotIn("EMAIL_PASS", child)
            with patch("config.ALLOW_CODE_EXECUTION", True):
                result = run_python_code(
                    "import os; print(os.getenv('GROQ_API_KEY', 'MISSING'))"
                )
        self.assertTrue(result["success"], result)
        self.assertEqual(result["output"], "MISSING")

    def test_oversized_code_refused(self):
        with patch("config.ALLOW_CODE_EXECUTION", True):
            result = run_python_code("x" * 20001)
        self.assertFalse(result["success"])


if __name__ == "__main__":
    unittest.main()
