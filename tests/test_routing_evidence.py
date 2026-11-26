"""Routing checks must never masquerade as OS execution success."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import stress_test_driver as driver


class RoutingEvidenceTests(unittest.TestCase):
    def test_recognized_action_is_not_verified_completion(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "routing.json"
            with (
                patch.object(driver, "TEST_CASES", ["open browser", "unsupported"]),
                patch.object(driver, "route_command", side_effect=[
                    {"action": "open_app", "target": "chrome"},
                    {"action": "unknown", "target": ""},
                ]),
            ):
                report = driver.run_routing_check(out)
            data = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(report["kind"], "routing_only")
        self.assertFalse(report["execution_attempted"])
        self.assertEqual(report["summary"]["total_cases"], 2)
        self.assertEqual(report["summary"]["routed_cases"], 1)
        self.assertEqual(report["summary"]["verified_completed_tasks"], 0)
        self.assertEqual(data["results"][0]["route_status"], "ROUTED")
        self.assertFalse(data["results"][0]["execution_attempted"])
        self.assertNotIn("success", data["results"][0])
        self.assertNotIn("PASSED", str(data))

    def test_router_error_is_not_marked_as_success(self):
        with tempfile.TemporaryDirectory() as folder:
            with (
                patch.object(driver, "TEST_CASES", ["bad command"]),
                patch.object(driver, "route_command", side_effect=ValueError("parser error")),
            ):
                report = driver.run_routing_check(Path(folder) / "report.json")
        self.assertEqual(report["summary"]["router_exceptions"], 1)
        self.assertEqual(report["summary"]["verified_completed_tasks"], 0)
        self.assertEqual(report["results"][0]["error_type"], "ValueError")


if __name__ == "__main__":
    unittest.main()
