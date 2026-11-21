"""Approval decisions are one-shot and require an actual local UI response."""
import threading
import unittest
from unittest.mock import MagicMock, patch

from core.action_policy import (
    ActionApprovalManager, check_action, get_action_approvals, needs_approval,
)
from utils.events import EventBus


class PolicyUnitTests(unittest.TestCase):
    def setUp(self):
        get_action_approvals().set_ui_ready(False)

    def test_high_impact_actions_require_confirmation(self):
        for action in ("delete_file", "execute_python", "mcp:server:exec",
                       "skill:communication", "automation:type", "capture_screen"):
            with self.subTest(action=action):
                self.assertTrue(needs_approval(action))
        self.assertFalse(needs_approval("chat"))
        self.assertFalse(needs_approval("list_files"))

    def test_headless_is_fail_closed(self):
        manager = ActionApprovalManager()
        self.assertFalse(manager.request("delete_file", "important.txt"))

    def test_single_use_confirmation_from_ui_callback(self):
        manager = ActionApprovalManager()
        bus = EventBus()
        manager.configure(bus)
        manager.set_ui_ready(True)
        tickets = []
        def show_dialog(payload):
            tickets.append(payload["request_id"])
            self.assertEqual(payload["action"], "delete_file")
            manager.respond(payload["request_id"], True)
        bus.subscribe("action_approval_requested", show_dialog)
        result = []
        worker = threading.Thread(target=lambda: result.append(manager.request("delete_file", "file.txt")))
        worker.start()
        worker.join(timeout=2)
        self.assertFalse(worker.is_alive())
        self.assertEqual(result, [True])
        self.assertFalse(manager.respond(tickets[0], True), "Approval ID cannot be reused")
        manager.set_ui_ready(False)

    def test_cancel_all_denies_pending(self):
        manager = ActionApprovalManager()
        bus = EventBus()
        manager.configure(bus)
        manager.set_ui_ready(True)
        started = threading.Event()
        bus.subscribe("action_approval_requested", lambda payload: started.set())
        results = []
        worker = threading.Thread(target=lambda: results.append(manager.request("power_state", "sleep")))
        worker.start()
        self.assertTrue(started.wait(2))
        manager.cancel_all()
        worker.join(timeout=2)
        self.assertEqual(results, [False])
        manager.set_ui_ready(False)

    def test_model_extra_cannot_fake_approval_for_registry(self):
        from core.action_registry import execute_action, ACTION_REGISTRY
        execute = MagicMock(return_value={"success": True})
        with patch.dict(ACTION_REGISTRY, {"delete_file": execute}):
            result = execute_action("delete_file", "file.txt", {"approved": True})
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "approval_required")
        execute.assert_not_called()

    def test_direct_skill_entrypoint_also_rejects_headless(self):
        import skills
        execute = MagicMock(return_value={"success": True})
        with patch.dict(skills._loaded_skills, {"fake": {"execute": execute}}):
            result = skills.execute_skill("fake", "dangerous request", {"approved": True})
        self.assertFalse(result["success"])
        execute.assert_not_called()

    def test_direct_agent_keyboard_and_screen_bypass_is_denied(self):
        from core.app import JarvisApp
        with (
            patch("core.app.agent_tools.type_text") as type_text,
            patch("core.app.agent_tools.press_key") as press_key,
            patch("core.app.agent_tools.read_screen") as screen,
        ):
            for tool in ("type_text", "press_key", "read_screen"):
                with self.subTest(tool=tool):
                    result = JarvisApp._execute_tool_step(object(), tool, "sensitive")
                    self.assertEqual(result["status"], "approval_required")
        type_text.assert_not_called()
        press_key.assert_not_called()
        screen.assert_not_called()

    def test_automation_click_denied_without_ui(self):
        from automation.executor import _execute_step
        from automation.plan import AutomationStep
        with patch("automation.executor.agent_tools.click") as click:
            result = _execute_step(AutomationStep(action="click", target="Submit"))
        self.assertEqual(result["status"], "approval_required")
        click.assert_not_called()


if __name__ == "__main__":
    unittest.main()
