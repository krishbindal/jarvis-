"""Only one command may mutate assistant state at a time."""
import threading
import unittest
from unittest.mock import patch

from core.app import JarvisApp
from utils.events import EventBus


class CommandGateTests(unittest.TestCase):
    def test_second_task_is_rejected_without_running(self):
        app = JarvisApp.__new__(JarvisApp)
        app._events = EventBus()
        app._command_gate = threading.BoundedSemaphore(1)
        app._command_admission = threading.Lock()
        app._command_cancel = threading.Event()
        results = []
        app._events.subscribe("command_result", results.append)

        started = threading.Event()
        release = threading.Event()
        def process(_payload):
            started.set()
            release.wait(3)

        with patch.object(app, "_process_command_threaded", side_effect=process) as executor:
            app._handle_command({"text": "open notepad"})
            self.assertTrue(started.wait(2))
            app._handle_command({"text": "open chrome"})
            self.assertTrue(results)
            self.assertEqual(results[-1]["status"], "busy")
            release.set()
            self.assertTrue(app._command_gate.acquire(timeout=2))
            app._command_gate.release()
            executor.assert_called_once()

    def test_interrupt_bypasses_busy_gate(self):
        app = JarvisApp.__new__(JarvisApp)
        app._events = EventBus()
        app._command_gate = threading.BoundedSemaphore(1)
        app._command_admission = threading.Lock()
        app._command_cancel = threading.Event()
        self.assertTrue(app._command_gate.acquire(blocking=False))
        events = []
        app._events.subscribe("command_result", events.append)
        with patch("core.action_policy.get_action_approvals") as get:
            app._handle_command({"text": "stop"})
        self.assertEqual(events[-1]["status"], "interrupt_requested")
        get.return_value.cancel_all.assert_called_once()
        self.assertTrue(app._command_cancel.is_set())
        app._command_gate.release()


if __name__ == "__main__":
    unittest.main()
