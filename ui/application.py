from __future__ import annotations

"""UI bootstrap helpers — launches both the main window and the floating overlay."""

import sys

from PySide6.QtWidgets import QApplication

from ui.main_window import JarvisWindow
from ui.overlay import JarvisOverlay
from utils import EventBus


def launch_ui(event_bus: EventBus) -> None:
    """Create and start the Qt application with main window + floating overlay."""
    app = QApplication.instance() or QApplication(sys.argv)

    # Main JARVIS window
    window = JarvisWindow(event_bus=event_bus)
    window.show()

    # Floating Overlay HUD (Phase 17)
    overlay = JarvisOverlay(event_bus=event_bus)
    overlay.show()

    # Wire toggle event so double-clicking overlay shows/hides main window
    def _toggle_main():
        if window.isVisible():
            window.hide()
        else:
            window.show()
            window.raise_()
            window.activateWindow()

    event_bus.subscribe("toggle_main_window", _toggle_main)

    app.exec()
