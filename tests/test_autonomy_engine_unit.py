import unittest
from datetime import datetime
from unittest.mock import patch

from brain.autonomy_engine import AutonomyEngine
from core.context_state import ContextState
from utils.events import EventBus


class AutonomyEngineTest(unittest.TestCase):
    def setUp(self):
        self.bus = EventBus()
        self.ctx = ContextState()
        self.suggestions = []
        self.bus.subscribe("autonomy_suggestion", self.suggestions.append)
        self.engine = AutonomyEngine(self.bus, self.ctx)

    @patch("brain.autonomy_engine.mark_pattern_suggested")
    @patch("brain.autonomy_engine.record_pattern")
    def test_pattern_detection_emits_suggestion(self, record_pattern, mark_pattern):
        record_pattern.return_value = {"count": 3, "last_suggested": None}
        self.engine._sequence.extend(["chrome", "youtube", "spotify"])

        self.engine._detect_pattern()

        self.assertTrue(self.suggestions)
        payload = self.suggestions[0]
        self.assertIn("entertainment mode", payload.get("label", ""))
        self.assertIn("Want me to prepare", payload.get("message", ""))
        mark_pattern.assert_called_once()

    @patch("brain.autonomy_engine.mark_task_run")
    @patch("brain.autonomy_engine.due_tasks")
    @patch("brain.autonomy_engine.execute_action")
    def test_scheduled_task_runs_with_self_healing(self, exec_action, due_tasks, mark_task):
        exec_action.return_value = {"success": True, "status": "success", "message": "ok"}
        due_tasks.return_value = [{
            "id": 1,
            "label": "Open Chrome",
            "command": "open chrome",
            "recur_seconds": 0,
            "auto_execute": True,
            "next_run": datetime.now(),
        }]

        self.engine._check_schedules()

        exec_action.assert_called_once()
        mark_task.assert_called_with(1, status="completed")


if __name__ == "__main__":
    unittest.main()
