"""No Qt event or animation timer may survive its owning window's shutdown."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import os
import unittest
from unittest.mock import patch

from utils import events
from utils.events import EventBus


class EventBusLifecycleTests(unittest.TestCase):
    def test_unsubscribe_detaches_callback(self):
        bus = EventBus()
        output = []
        def listener(payload):
            output.append(payload)
        bus.subscribe("notification", listener)
        bus.emit("notification", 1)
        self.assertEqual(output, [1])
        self.assertTrue(bus.unsubscribe("notification", listener))
        self.assertFalse(bus.unsubscribe("notification", listener))
        bus.emit("notification", 2)
        self.assertEqual(output, [1])
        self.assertFalse(bus._handlers.get("notification"))

    def test_bound_method_can_be_unsubscribed(self):
        bus = EventBus()
        class Receiver:
            def __init__(self):
                self.count = 0
            def on_event(self, _):
                self.count += 1
        receiver = Receiver()
        bus.subscribe("tick", receiver.on_event)
        self.assertTrue(bus.unsubscribe("tick", receiver.on_event))
        bus.emit("tick", 123)
        self.assertEqual(receiver.count, 0)

    def test_singleton_creation_is_safe_under_races(self):
        with patch.object(events, "_event_bus", None):
            with ThreadPoolExecutor(max_workers=12) as pool:
                instances = list(pool.map(lambda _: events.get_event_bus(), range(50)))
            self.assertEqual(len({id(x) for x in instances}), 1)


@unittest.skipUnless(importlib.util.find_spec("PySide6") is not None, "Qt not installed")
class QtLifecycleTests(unittest.TestCase):
    def test_windows_unregister_handlers_and_stop_all_timers(self):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PySide6.QtWidgets import QApplication
        from ui.main_window import JarvisWindow
        from ui.overlay import JarvisOverlay

        app = QApplication.instance() or QApplication([])
        app.setQuitOnLastWindowClosed(False)
        bus = EventBus()
        window = JarvisWindow(bus)
        overlay = JarvisOverlay(bus)
        window.show()
        overlay.show()
        app.processEvents()

        self.assertEqual(len(bus._handlers["command_result"]), 2)
        self.assertEqual(len(bus._handlers["action_approval_requested"]), 1)
        overlay._on_command_result({"message": "Working"})
        overlay._on_proactive_notification({"message": "A suggestion"})
        self.assertTrue(overlay._status_reset_timer.isActive())
        self.assertTrue(overlay._proactive_timer.isActive())

        window.close()
        overlay.close()
        app.processEvents()
        self.assertFalse(overlay._timer.isActive())
        self.assertFalse(overlay._status_reset_timer.isActive())
        self.assertFalse(overlay._proactive_timer.isActive())
        self.assertFalse(window._typing_timer.isActive())
        self.assertFalse(window.hud._timer.isActive())
        self.assertFalse(window.hud._stats_timer.isActive())
        self.assertEqual(len(bus._handlers.get("command_result", [])), 0)
        self.assertEqual(len(bus._handlers.get("action_approval_requested", [])), 0)
        self.assertEqual(len(bus._handlers.get("proactive_notification", [])), 0)
        bus.emit("command_result", {"message": "After close"})  # No stale slots
        app.quit()


if __name__ == "__main__":
    unittest.main()
