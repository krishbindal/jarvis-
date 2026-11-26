"""Reminders should have distinct IDs and be cancelled on shutdown."""
import unittest
from unittest.mock import MagicMock, patch

from skills import reminder


class ReminderLifecycleTests(unittest.TestCase):
    def tearDown(self):
        reminder.cancel_all_reminders()

    def test_unique_ids_after_cancel_and_recreate(self):
        with patch.object(reminder.threading, "Timer") as factory:
            factory.side_effect = lambda *a, **kw: MagicMock()
            first = reminder.execute("remind me in 3 seconds to do a")
            self.assertTrue(first["success"])
            reminder.cancel_all_reminders()
            second = reminder.execute("remind me in 4 seconds to do b")
        self.assertTrue(second["success"])
        self.assertNotEqual(first["output"], second["output"])

    def test_shutdown_cancels_all_pending(self):
        with patch.object(reminder.threading, "Timer") as factory:
            timers = [MagicMock(), MagicMock()]
            factory.side_effect = timers
            reminder.execute("remind me in 1 minute to a")
            reminder.execute("remind me in 2 minutes to b")
            self.assertEqual(reminder.cancel_all_reminders(), 2)
            self.assertEqual(reminder.cancel_all_reminders(), 0)
            for timer in timers:
                timer.cancel.assert_called_once()

    def test_rejects_unbounded_timer(self):
        result = reminder.execute("remind me in 99999999 hours to crash")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "invalid_reminder")

    def test_capacity_limit(self):
        with patch.object(reminder, "_MAX_ACTIVE", 0):
            result = reminder.execute("remind me in 5 seconds to test")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "capacity_reached")


if __name__ == "__main__":
    unittest.main()
