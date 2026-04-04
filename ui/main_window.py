from __future__ import annotations

"""Jarvis-themed UI with command emission and logging."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPalette, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from utils import EventBus


ACCENT = "#00ffff"
BACKGROUND = "#000000"


class JarvisWindow(QMainWindow):
    """Futuristic themed window for JARVIS-X."""

    def __init__(self, event_bus: EventBus) -> None:
        super().__init__()
        self._events = event_bus
        self.setWindowTitle("JARVIS-X")
        self.setMinimumSize(960, 640)
        self._apply_palette()
        self._build_layout()
        self._events.subscribe("command_result", self._on_command_result)

    def _apply_palette(self) -> None:
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(BACKGROUND))
        palette.setColor(QPalette.WindowText, QColor(ACCENT))
        palette.setColor(QPalette.Base, QColor("#050505"))
        palette.setColor(QPalette.Text, QColor("#e0ffff"))
        palette.setColor(QPalette.Button, QColor("#021018"))
        palette.setColor(QPalette.ButtonText, QColor(ACCENT))
        self.setPalette(palette)

    def _build_layout(self) -> None:
        main = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("JARVIS-X — LOCAL AI ASSISTANT")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont("Segoe UI Semibold", 21)
        title_font.setLetterSpacing(QFont.PercentageSpacing, 115)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {ACCENT}; text-transform: uppercase;")

        self.status_label = QLabel("Status: Idle")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #36d7ff; font-size: 14px;")

        hud = HUDWidget()
        hud.setFixedHeight(240)

        self.command_input = QLineEdit()
        command_input.setPlaceholderText("Type a command or speak after the chime...")
        command_input.setStyleSheet(
            f"""
            QLineEdit {{
                padding: 12px;
                border: 1px solid #005f6a;
                border-radius: 10px;
                background: #050b11;
                color: #e0ffff;
            }}
            QLineEdit:focus {{
                border: 1px solid {ACCENT};
                box-shadow: 0 0 12px {ACCENT}33;
            }}
            """
        )

        self.command_input.returnPressed.connect(self._emit_command)

        execute = QPushButton("Engage")
        execute.setCursor(Qt.PointingHandCursor)
        execute.setStyleSheet(
            f"""
            QPushButton {{
                padding: 12px;
                background-color: #021018;
                color: {ACCENT};
                border: 1px solid {ACCENT};
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background-color: #032536;
            }}
            QPushButton:pressed {{
                background-color: #021621;
            }}
            """
        )

        execute.clicked.connect(self._emit_command)

        command_row = QHBoxLayout()
        command_row.setSpacing(10)
        command_row.addWidget(self.command_input, stretch=1)
        command_row.addWidget(execute)

        log_label = QLabel("Command Log")
        log_label.setStyleSheet(f"color: {ACCENT}; font-size: 13px;")

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setPlaceholderText("System logs and responses will appear here.")
        self.console.setFrameStyle(QFrame.NoFrame)
        self.console.setStyleSheet(
            """
            QTextEdit {
                background: #050b11;
                color: #9cf6ff;
                border: 1px solid #005f6a;
                border-radius: 12px;
                padding: 12px;
            }
            """
        )

        layout.addWidget(title)
        layout.addWidget(self.status_label)
        layout.addWidget(hud)
        layout.addLayout(command_row)
        layout.addWidget(log_label)
        layout.addWidget(self.console, stretch=1)

        main.setLayout(layout)
        self.setCentralWidget(main)

    def _emit_command(self) -> None:
        text = self.command_input.text().strip()
        if not text:
            return
        self._append_log(f"YOU: {text}")
        self.command_input.clear()
        self._events.emit("command_received", {"text": text})
        self.status_label.setText("Status: Processing command...")

    def _on_command_result(self, payload: dict) -> None:
        message = payload.get("message") or "Command processed."
        action = payload.get("action", "")
        target = payload.get("target", "")
        detail = f"{message} ({action} -> {target})".strip()
        self._append_log(f"SYSTEM: {detail}")
        self.status_label.setText("Status: Idle")

    def _append_log(self, line: str) -> None:
        self.console.append(line)


class HUDWidget(QWidget):
    """Lightweight circular HUD animation."""

    def __init__(self) -> None:
        super().__init__()
        self._angle = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)

    def _tick(self) -> None:
        self._angle = (self._angle + 2.5) % 360
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(BACKGROUND))

        center = self.rect().center()
        radius = min(self.width(), self.height()) // 2 - 14
        accent = QColor(ACCENT)

        rings = [radius, int(radius * 0.72), int(radius * 0.48)]
        widths = [2, 2, 2]
        for r, w in zip(rings, widths, strict=False):
            pen = QPen(accent)
            pen.setWidth(w)
            pen.setCosmetic(True)
            pen.setStyle(Qt.DotLine if r != radius else Qt.SolidLine)
            painter.setPen(pen)
            painter.drawEllipse(center, r, r)

        pen = QPen(accent)
        pen.setWidth(3)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        start_angle = int(self._angle * 16)
        span_angle = int(120 * 16)
        painter.drawArc(
            center.x() - rings[1],
            center.y() - rings[1],
            rings[1] * 2,
            rings[1] * 2,
            start_angle,
            span_angle,
        )
