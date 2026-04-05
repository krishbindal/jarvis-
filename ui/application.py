from __future__ import annotations

"""UI bootstrap helpers — launches both the main window and the floating overlay."""

import sys

from PySide6.QtWidgets import QApplication

from ui.main_window import JarvisWindow
from ui.overlay import JarvisOverlay
from utils import EventBus


def launch_ui(event_bus: EventBus) -> None:
    """Create and start the Qt application with main window + floating overlay."""
    from utils.logger import get_logger
    ui_logger = get_logger("ui.launch")
    ui_logger.info("Initializing Qt application...")

    try:
        app = QApplication.instance() or QApplication(sys.argv)
        ui_logger.info("QApplication created.")

        # Main JARVIS window
        window = JarvisWindow(event_bus=event_bus)
        window.show()
        ui_logger.info("Main window displayed.")

        # Floating Overlay HUD (Phase 17)
        overlay = JarvisOverlay(event_bus=event_bus)
        overlay.show()
        ui_logger.info("Overlay HUD displayed.")

        # Wire toggle event so double-clicking overlay shows/hides main window
        def _toggle_main():
            if window.isVisible():
                window.hide()
            else:
                window.show()
                window.raise_()
                window.activateWindow()

        event_bus.subscribe("toggle_main_window", _toggle_main)

        ui_logger.info("Entering event loop...")
        exit_code = app.exec()
        ui_logger.info("Event loop exited with code: %s", exit_code)

    except Exception as e:
        ui_logger.error("Fatal error during UI launch: %s", e, exc_info=True)
        raise
