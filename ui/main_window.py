from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPalette
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class JarvisWindow(QMainWindow):
    """Futuristic themed window for JARVIS-X."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("JARVIS-X")
        self.setMinimumSize(900, 600)
        self._apply_palette()
        self._build_layout()

    def _apply_palette(self) -> None:
        palette = QPalette()
        gradient = QLinearGradient(0, 0, 0, 1)
        gradient.setCoordinateMode(QLinearGradient.ObjectBoundingMode)
        gradient.setColorAt(0.0, QColor("#0b0f1a"))
        gradient.setColorAt(1.0, QColor("#0d1626"))
        palette.setBrush(QPalette.Window, gradient)
        palette.setColor(QPalette.WindowText, QColor("#b7e3ff"))
        palette.setColor(QPalette.Base, QColor("#0f1524"))
        palette.setColor(QPalette.Text, QColor("#c8f1ff"))
        palette.setColor(QPalette.Button, QColor("#122034"))
        palette.setColor(QPalette.ButtonText, QColor("#8be7ff"))
        self.setPalette(palette)

    def _build_layout(self) -> None:
        main = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("JARVIS-X — Local AI Assistant")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont("Segoe UI Semibold", 20)
        title_font.setLetterSpacing(QFont.PercentageSpacing, 110)
        title.setFont(title_font)
        title.setStyleSheet("color: #9cf6ff; text-transform: uppercase;")

        status = QLabel("System ready. Awaiting command input.")
        status.setAlignment(Qt.AlignCenter)
        status.setStyleSheet("color: #5fd2ff;")

        command_input = QLineEdit()
        command_input.setPlaceholderText("Type a command or speak after the chime...")
        command_input.setStyleSheet(
            """
            QLineEdit {
                padding: 12px;
                border: 1px solid #1e3a5c;
                border-radius: 10px;
                background: #0f1c2f;
                color: #c8f1ff;
            }
            QLineEdit:focus {
                border: 1px solid #2fe0ff;
                box-shadow: 0 0 12px #2fe0ff33;
            }
            """
        )

        execute = QPushButton("Engage")
        execute.setCursor(Qt.PointingHandCursor)
        execute.setStyleSheet(
            """
            QPushButton {
                padding: 12px;
                background-color: #183657;
                color: #9cf6ff;
                border: 1px solid #2fe0ff;
                border-radius: 12px;
            }
            QPushButton:hover {
                background-color: #1f4a79;
            }
            QPushButton:pressed {
                background-color: #122c46;
            }
            """
        )

        console = QTextEdit()
        console.setReadOnly(True)
        console.setPlaceholderText("System logs and responses will appear here.")
        console.setFrameStyle(QFrame.NoFrame)
        console.setStyleSheet(
            """
            QTextEdit {
                background: #0c1321;
                color: #9cf6ff;
                border: 1px solid #1e3a5c;
                border-radius: 12px;
                padding: 12px;
            }
            """
        )

        layout.addWidget(title)
        layout.addWidget(status)
        layout.addWidget(command_input)
        layout.addWidget(execute)
        layout.addWidget(console, stretch=1)

        main.setLayout(layout)
        self.setCentralWidget(main)
