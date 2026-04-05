from __future__ import annotations

"""Jarvis-themed UI with command emission and logging."""

import os
import sys
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QColor, QFont, QPalette, QPainter, QPen, QLinearGradient, QTextCursor
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
    QGraphicsDropShadowEffect,
)

from utils import EventBus
from utils.system_context import get_system_stats
import math

# UI Constants
ACCENT = "#00ffff"
NEON_GLOW = "rgba(0, 255, 255, 120)"

class JarvisWindow(QMainWindow):
    """Modern, Glassmorphism-themed window for JARVIS-X."""

    def __init__(self, event_bus: EventBus) -> None:
        super().__init__()
        self._events = event_bus
        self.setWindowTitle("JARVIS-X")
        self.setMinimumSize(1000, 700)
        
        # Frameless and Transparent
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self._setup_glass_effect()
        self._build_layout()
        self._load_styles()
        
        self._events.subscribe("command_result", self._on_command_result)
        self._events.subscribe("stream_output", self._on_stream_output)
        self._events.subscribe("cinematic_log", self._on_cinematic_log)
        self._events.subscribe("command_progress", self._on_command_progress)
        self._drag_pos = QPoint()
        self._streaming = False
        self._typing_timer = QTimer(self)
        self._typing_timer.timeout.connect(self._type_tick)
        self._type_queue = []
        self._current_line = ""
        self._type_index = 0

    def _setup_glass_effect(self) -> None:
        """Enable Windows 11 Acrylic effect if available."""
        try:
            from winmica import ApplyMica
            # Apply Mica/Acrylic to the HWND
            ApplyMica(int(self.winId()), True) # Dark Mode Acrylic
        except Exception:
            pass

    def _load_styles(self) -> None:
        qss_path = os.path.join(os.path.dirname(__file__), "styles.qss")
        if os.path.exists(qss_path):
            with open(qss_path, "r") as f:
                self.setStyleSheet(f.read())

    def _build_layout(self) -> None:
        self.central = QWidget()
        self.central.setObjectName("CentralWidget")
        self.setCentralWidget(self.central)
        
        layout = QVBoxLayout(self.central)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # Custom Title Bar / Header
        header = QHBoxLayout()
        self.title_label = QLabel("JARVIS-X // COPILOT")
        self.title_label.setObjectName("Title")
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("background: transparent; border: none; font-size: 18px; color: #ff5555;")
        close_btn.clicked.connect(self.close)
        
        header.addWidget(self.title_label)
        header.addStretch()
        header.addWidget(close_btn)

        self.status_label = QLabel("SYSTEM READY")
        self.status_label.setObjectName("Status")
        self.status_label.setAlignment(Qt.AlignCenter)

        # HUD Section
        hud_container = QWidget()
        hud_container.setFixedHeight(260)
        hud_layout = QVBoxLayout(hud_container)
        self.hud = HUDWidget()
        hud_layout.addWidget(self.hud)

        # Input Section
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Direct system command input...")
        self.command_input.returnPressed.connect(self._emit_command)

        execute = QPushButton("ENGAGE")
        execute.setCursor(Qt.PointingHandCursor)
        execute.clicked.connect(self._emit_command)

        input_row = QHBoxLayout()
        input_row.setSpacing(12)
        input_row.addWidget(self.command_input, stretch=1)
        input_row.addWidget(execute)

        # Documentation / console
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setPlaceholderText("Awaiting neural link...")
        
        layout.addLayout(header)
        layout.addWidget(self.status_label)
        layout.addWidget(hud_container)
        layout.addLayout(input_row)
        layout.addWidget(self.console, stretch=1)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def _emit_command(self) -> None:
        text = self.command_input.text().strip()
        if not text:
            return
        self._append_log(f"USR > {text}")
        self.command_input.clear()
        self._events.emit("command_received", {"text": text})
        self.status_label.setText("ANALYZING...")

    def _on_command_result(self, payload: dict) -> None:
        message = payload.get("message") or "Logic complete."
        action = payload.get("action", "")
        self._append_log(f"JARVIS > {message}")
        self.status_label.setText("SYSTEM READY")
        self._streaming = False

    def _append_log(self, line: str) -> None:
        self.console.append(line)

    def _on_stream_output(self, payload: dict) -> None:
        token = payload.get("token", "")
        reset = payload.get("reset", False)
        if reset or not self._streaming:
            self.console.append("")
            self._streaming = True
        cursor = self.console.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(token)
        self.console.setTextCursor(cursor)

    def _on_cinematic_log(self, payload: dict) -> None:
        text = payload.get("text", "")
        if not text:
            return
        self._queue_type_line(text)

    def _on_command_progress(self, payload: dict) -> None:
        text = payload.get("text", "")
        if text:
            self.status_label.setText(text.upper())
            self._queue_type_line(f"[STATUS] {text}")

    def _queue_type_line(self, text: str) -> None:
        if self._typing_timer.isActive():
            self._type_queue.append(text)
            return
        self.console.append("")
        self._current_line = text
        self._type_index = 0
        self._typing_timer.start(12)

    def _type_tick(self) -> None:
        if self._type_index >= len(self._current_line):
            self._typing_timer.stop()
            if self._type_queue:
                next_line = self._type_queue.pop(0)
                self.console.append("")
                self._current_line = next_line
                self._type_index = 0
                self._typing_timer.start(12)
            return

        cursor = self.console.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(self._current_line[self._type_index])
        self.console.setTextCursor(cursor)
        self._type_index += 1


class HUDWidget(QWidget):
    """Futuristic circular HUD with neon glow and high-end gradients."""

    def __init__(self) -> None:
        super().__init__()
        self._angle = 0.0
        self._pulse = 0.0
        self._stats = {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "battery_percent": None,
            "active_window": "System"
        }
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30) # Animation Timer
        
        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._update_stats)
        self._stats_timer.start(1000) # 1Hz Stats Update

    def _tick(self) -> None:
        # Rotation speed based on CPU Load: Base 1.0 + Scale 0.1 * CPU%
        rotation_speed = 1.0 + (self._stats["cpu_percent"] * 0.1)
        self._angle = (self._angle + rotation_speed) % 360
        self._pulse = (self._pulse + 0.05) % 6.28 # Sin Wave for Pulse
        self.update()

    def _update_stats(self) -> None:
        self._stats = get_system_stats()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        center = self.rect().center()
        radius = min(self.width(), self.height()) // 2 - 20
        
        # Base pulsing glow
        import math
        alpha = int(100 + 50 * math.sin(self._pulse))
        accent = QColor(0, 255, 255, alpha)
        
        # Outer Ring
        pen = QPen(accent)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawEllipse(center, radius, radius)
        
        # Rotating Arcs
        pen.setWidth(4)
        painter.setPen(pen)
        painter.drawArc(
            center.x() - radius, center.y() - radius, radius * 2, radius * 2,
            int(self._angle * 16), int(60 * 16)
        )
        painter.drawArc(
            center.x() - radius, center.y() - radius, radius * 2, radius * 2,
            int((self._angle + 180) * 16), int(60 * 16)
        )
        
        # Inner Data Rings
        inner_r = int(radius * 0.7)
        pen.setWidth(1)
        pen.setStyle(Qt.DotLine)
        painter.setPen(pen)
        painter.drawEllipse(center, inner_r, inner_r)
        
        # Scanning line
        pen.setStyle(Qt.SolidLine)
        pen.setWidth(2)
        painter.setPen(pen)
        scan_angle = (self._angle * 2) % 360
        px = center.x() + inner_r * math.cos(math.radians(scan_angle))
        py = center.y() + inner_r * math.sin(math.radians(scan_angle))
        painter.drawLine(center.x(), center.y(), int(px), int(py))
        
        # Performance Overlay (Neural Metadata)
        painter.setPen(QColor(0, 255, 255, 180))
        painter.setFont(QFont("Segoe UI Semibold", 8))
        
        # Bottom Left: Window Info
        win_text = (self._stats["active_window"][:25] + "..") if len(self._stats["active_window"]) > 25 else self._stats["active_window"]
        painter.drawText(center.x() - radius, center.y() + radius + 15, f"CTX: {win_text.upper()}")
        
        # Top Right: CPU/RAM
        painter.drawText(center.x() + radius - 60, center.y() - radius - 5, f"CPU: {int(self._stats['cpu_percent'])}%")
        painter.drawText(center.x() + radius - 60, center.y() - radius + 10, f"RAM: {int(self._stats['memory_percent'])}%")
        
        # Bottom Right: Battery
        if self._stats["battery_percent"] is not None:
            painter.drawText(center.x() + radius - 60, center.y() + radius + 15, f"PWR: {int(self._stats['battery_percent'])}%")
