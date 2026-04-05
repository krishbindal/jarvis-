from unittest import TestCase
from unittest.mock import patch

from automation.plan import AutomationPlan, AutomationStep
from automation.planner import build_automation_plan
from automation.executor import execute_automation_plan


class DummyContext:
    def __init__(self):
        self.current_app = None
        self.updates = []

    def snapshot(self):
        return {"current_app": self.current_app}

    def update_after_action(self, action, target, extra, exec_result):
        self.current_app = (extra or {}).get("app") or self.current_app
        self.updates.append((action, target, extra, exec_result))


class AutomationPlannerTests(TestCase):
    @patch("automation.planner._call_provider", return_value={})
    def test_fallback_plan_splits_multi_step(self, _):
        plan = build_automation_plan("open chrome and search python tutorial", context={})
        self.assertTrue(plan.is_actionable())
        self.assertEqual(plan.steps[0].action, "open_app")
        self.assertEqual(plan.steps[1].action, "search")
        self.assertIn("python tutorial", plan.steps[1].target)


class AutomationExecutorTests(TestCase):
    @patch("automation.executor._scroll", return_value={"success": True, "status": "success", "message": "Scrolled"})
    @patch("automation.executor.download_file", return_value={"success": True, "status": "success", "message": "downloaded"})
    @patch("automation.executor.execute_action", return_value={"success": True, "status": "success", "message": "opened", "resolved_target": "https://example.com"})
    @patch("automation.executor.agent_tools.click", return_value={"success": True, "status": "success", "message": "clicked"})
    @patch("automation.executor.agent_tools.type_text", return_value={"success": True, "status": "success", "message": "typed"})
    @patch("automation.executor.agent_tools.open_app", return_value={"success": True, "status": "success", "message": "opened", "app_used": "chrome"})
    def test_execute_plan_runs_steps(self, *_mocks):
        plan = AutomationPlan(
            goal="test",
            steps=[
                AutomationStep(action="open_app", target="chrome", app="chrome"),
                AutomationStep(action="search", target="python tutorial", app="chrome"),
                AutomationStep(action="click", target=""),
                AutomationStep(action="type", target="hello world"),
                AutomationStep(action="scroll", target="-500"),
            ],
            source="test",
        )
        ctx = DummyContext()
        result = execute_automation_plan(plan, ctx, events=None, interactions=None)
        self.assertTrue(result["success"])
        self.assertEqual(len(result["steps"]), 5)
        self.assertEqual(ctx.current_app, "chrome")
