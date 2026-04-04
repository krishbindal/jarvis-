from __future__ import annotations

"""UI bootstrap helpers."""

import sys

from PySide6.QtWidgets import QApplication

from ui.main_window import JarvisWindow
from utils import EventBus


def launch_ui(event_bus: EventBus) -> None:
    """Create and start the Qt application."""
    app = QApplication.instance() or QApplication(sys.argv)
    window = JarvisWindow(event_bus=event_bus)
    window.show()
    app.exec()
