"""Real executor outcomes must decide task status; AI text never does."""
import unittest
from core.execution_evidence import normalize_executor_result, summarize_execution_results
from automation.plan import AutomationPlan, AutomationStep
from automation.executor import execute_automation_plan
from unittest.mock import patch


class ExecutionEvidenceTests(unittest.TestCase):
    def test_no_success_flag_is_not_success(self):
        result = normalize_executor_result({"status": "success", "message": "Done"})
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "unverified")

    def test_non_dict_tool_output_is_not_success(self):
        result = normalize_executor_result("Task completed", "open_app")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "invalid_result")

    def test_conflicting_status_is_rejected(self):
        result = normalize_executor_result({"status": "error", "success": True})
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "inconsistent_result")

    def test_explicit_bool_success_is_preserved(self):
        result = normalize_executor_result({"success": True, "message": "opened"})
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "success")

    def test_no_steps_never_means_completed(self):
        summary = summarize_execution_results([], expected=3)
        self.assertFalse(summary["success"])
        self.assertEqual(summary["status"], "not_executed")

    def test_partial_does_not_echo_planner_claim(self):
        summary = summarize_execution_results(
            [{"success": True, "message": "opened"},
             {"success": False, "message": "not found"}], expected=3,
        )
        self.assertFalse(summary["success"])
        self.assertIn("1/3", summary["message"])
        self.assertNotIn("Task complete", summary["message"])

    def test_automation_ignores_hallucinated_planner_confirmation(self):
        plan = AutomationPlan(
            goal="test",
            message="Absolutely completed all tasks",
            steps=[AutomationStep(action="open_app", target="notepad"),
                   AutomationStep(action="open_app", target="chrome")],
        )
        with patch("automation.executor._execute_step", side_effect=[
            {"success": True, "status": "success", "message": "started"},
            {"status": "success", "message": "claimed complete"},
        ]):
            report = execute_automation_plan(plan)
        self.assertFalse(report["success"])
        self.assertEqual(report["attempted_steps"], 2)
        self.assertIn("1/2", report["message"])
        self.assertNotIn("Absolutely completed", report["message"])

    def test_agent_empty_plan_never_claims_completion(self):
        from core.app import JarvisApp
        report = JarvisApp._agent_report([], "Task complete.")
        self.assertFalse(report["success"])
        self.assertEqual(report["status"], "not_executed")
        self.assertNotIn("Task complete.", report["message"])


if __name__ == "__main__":
    unittest.main()
