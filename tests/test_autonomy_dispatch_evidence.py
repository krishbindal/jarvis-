"""Scheduler must never record a command-queued event as task completion."""
import unittest
from unittest.mock import MagicMock, patch

from brain.autonomy_engine import AutonomyEngine
from core.context_state import ContextState
from utils.events import EventBus


def scheduled_task(command="find my documents", recurring=0):
    return {
        "id": 3, "label": "Scheduled", "command": command,
        "recur_seconds": recurring, "auto_execute": True,
    }


class AutonomyOutcomeTests(unittest.TestCase):
    def setUp(self):
        self.bus = EventBus()
        self.context = ContextState()
        self.engine = AutonomyEngine(self.bus, self.context)

    def test_non_open_command_is_only_dispatched_not_completed(self):
        observed = []
        self.bus.subscribe("command_received", observed.append)
        with (
            patch("brain.autonomy_engine.due_tasks", return_value=[scheduled_task()]),
            patch("brain.autonomy_engine.mark_task_run") as mark,
        ):
            self.engine._check_schedules()
        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0]["source"], "autonomy")
        mark.assert_called_once_with(3, status="dispatched_unverified")

    def test_recurring_dispatched_command_preserves_recurrence_not_success(self):
        with (
            patch("brain.autonomy_engine.due_tasks", return_value=[scheduled_task(recurring=60)]),
            patch("brain.autonomy_engine.mark_task_run") as mark,
        ):
            self.engine._check_schedules()
        mark.assert_called_once_with(3, status="recurring")

    def test_missing_success_field_does_not_count_as_success(self):
        with (
            patch("brain.autonomy_engine.execute_action",
                  side_effect=[{"status": "success"}, {"success": False, "status": "unverified"}]) as execute,
            patch.object(self.context, "update_after_action") as context,
        ):
            outcome = self.engine._execute_safe_command("open notepad")
        self.assertIs(outcome, False)
        self.assertEqual(execute.call_count, 2)
        context.assert_not_called()

    def test_verified_open_result_can_complete_task(self):
        with (
            patch("brain.autonomy_engine.due_tasks", return_value=[scheduled_task(command="open notepad")]),
            patch("brain.autonomy_engine.mark_task_run") as mark,
            patch("brain.autonomy_engine.execute_action",
                  return_value={"success": True, "status": "success"}) as execute,
        ):
            self.engine._check_schedules()
        execute.assert_called_once_with("open_app", "notepad")
        mark.assert_called_once_with(3, status="completed")

    def test_already_active_nonrecurring_task_is_skipped_not_completed(self):
        self.context.update_after_action("open_app", "notepad.exe", {}, {"success": True, "status": "success"})
        with (
            patch("brain.autonomy_engine.due_tasks", return_value=[scheduled_task(command="open notepad")]),
            patch("brain.autonomy_engine.mark_task_run") as mark,
        ):
            self.engine._check_schedules()
        mark.assert_called_once_with(3, status="skipped_active")

    def test_compound_open_command_is_queued_not_passed_as_app_name(self):
        events = []
        self.bus.subscribe("command_received", events.append)
        with patch("brain.autonomy_engine.execute_action") as executor:
            result = self.engine._execute_safe_command("open chrome and search for laptops")
        self.assertIsNone(result)
        self.assertEqual(len(events), 1)
        executor.assert_not_called()

    def test_unavailable_executor_dispatches_but_never_confirms(self):
        events = []
        self.bus.subscribe("command_received", events.append)
        with patch("brain.autonomy_engine.execute_action", None):
            outcome = self.engine._execute_safe_command("open firefox")
        self.assertIsNone(outcome)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["source"], "autonomy")


if __name__ == "__main__":
    unittest.main()
