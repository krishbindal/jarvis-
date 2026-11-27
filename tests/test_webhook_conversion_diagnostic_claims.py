"""System-check tool acknowledgment must never imply device validation."""
import unittest
from unittest.mock import patch

from core import action_registry
from executor import system_executor


class DiagnosticClaimTests(unittest.TestCase):
    def test_action_registry_reports_noninvasive_inventory_only(self):
        with patch.object(action_registry.subprocess, "check_output", return_value="Release status: NOT VERIFIED\n"):
            result = action_registry.execute_action("system_check", "")
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "diagnostic_report_generated")
        self.assertIn("does NOT verify", result["message"])
        self.assertNotIn("full system check", result["message"].lower())

    def test_system_executor_reports_limits(self):
        with patch.object(system_executor.subprocess, "check_output", return_value="NOT VERIFIED"):
            result = system_executor.run_system_check()
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "diagnostic_report_generated")
        self.assertIn("NOT tested", result["message"])
        self.assertNotIn("fully operational", result["message"].lower())


if __name__ == "__main__":
    unittest.main()
