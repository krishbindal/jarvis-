import threading
import unittest
from unittest.mock import patch

from automation.executor import execute_automation_plan
from automation.plan import AutomationPlan, AutomationStep


class AutomationCancellationEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.plan = AutomationPlan("test", [AutomationStep("open_app", "one"), AutomationStep("open_app", "two")])

    def test_cancel_before_first_step(self):
        event = threading.Event()
        event.set()
        with patch("automation.executor._execute_step") as execute:
            result = execute_automation_plan(self.plan, cancel_event=event)
        execute.assert_not_called()
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "cancelled")

    def test_cancel_after_first_step(self):
        event = threading.Event()
        def execute(*args):
            event.set()
            return {"success": True, "status": "success", "message": "observed"}
        with patch("automation.executor._execute_step", side_effect=execute) as tool:
            result = execute_automation_plan(self.plan, cancel_event=event)
        tool.assert_called_once()
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(len(result["steps"]), 1)

    def test_exception_preserves_previous_result(self):
        with patch("automation.executor._execute_step", side_effect=[
            {"success": True, "status": "success", "message": "observed"},
            RuntimeError("unexpected"),
        ]):
            result = execute_automation_plan(self.plan)
        self.assertFalse(result["success"])
        self.assertEqual(len(result["steps"]), 2)
        self.assertTrue(result["steps"][0]["success"])
        self.assertFalse(result["steps"][1]["success"])


if __name__ == "__main__":
    unittest.main()
