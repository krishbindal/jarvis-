"""Reject invented skills, oversize plans, fake permissions and model code."""
import unittest
from core.plan_guard import validate_ai_action_plan


class PlanGuardTests(unittest.TestCase):
    def setUp(self):
        self.allowed = {"open_app": object(), "execute_python": object(), "chat": object()}

    def validate(self, steps, **kw):
        return validate_ai_action_plan(steps, self.allowed, **kw)

    def test_known_action_is_allowed(self):
        plan = self.validate([{"action": "open_app", "target": "notepad", "extra": {}}])
        self.assertEqual(plan["steps"][0]["target"], "notepad")

    def test_unknown_tool_is_not_invented(self):
        plan = self.validate([{"action": "teleport_files", "target": "x"}])
        self.assertIn("error", plan)

    def test_unknown_skill_is_rejected(self):
        plan = self.validate([{"action": "skill:arbitrary", "target": "hello"}])
        self.assertIn("error", plan)

    def test_known_skill_can_be_proposed(self):
        plan = self.validate(
            [{"action": "skill:browser", "target": "open a page"}],
            loaded_skills={"browser"},
        )
        self.assertEqual(plan["steps"][0]["action"], "skill:browser")

    def test_model_made_approval_is_rejected(self):
        plan = self.validate([{
            "action": "open_app", "target": "notepad",
            "extra": {"approved": True},
        }])
        self.assertIn("error", plan)

    def test_extra_must_be_json_dict(self):
        plan = self.validate([{"action": "open_app", "target": "notepad", "extra": ["fake"]}])
        self.assertIn("error", plan)

    def test_overlong_plan_fails_closed(self):
        plan = self.validate([{"action": "open_app", "target": f"app{i}"} for i in range(4)])
        self.assertIn("error", plan)

    def test_empty_target_rejected_when_needed(self):
        plan = self.validate([{"action": "open_app", "target": ""}])
        self.assertIn("error", plan)

    def test_code_execution_requires_separate_user_opt_in(self):
        plan = self.validate([{"action": "execute_python", "target": "print(2)"}])
        self.assertIn("error", plan)
        allowed = self.validate([{"action": "execute_python", "target": "print(2)"}], allow_model_code=True)
        self.assertNotIn("error", allowed)

    def test_target_must_not_include_null(self):
        self.assertIn("error", self.validate([{"action": "open_app", "target": "bad\x00"}]))


if __name__ == "__main__":
    unittest.main()
