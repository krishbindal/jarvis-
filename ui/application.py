from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from ui.main_window import JarvisWindow


def launch_ui() -> None:
    """Create and start the Qt application."""
    app = QApplication.instance() or QApplication(sys.argv)
    window = JarvisWindow()
    window.show()
    app.exec()
