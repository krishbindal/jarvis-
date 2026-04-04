"""
JARVIS-X Phase 17: Floating Overlay HUD (The "Look")

A transparent, always-on-top pill-shaped bar that sits at the top of the screen.
Shows real-time status, voice waveforms, and visual feedback.
"""

from __future__ import annotations

import math
import random
from PySide6.QtCore import (
    Qt, QTimer, QRectF, QPropertyAnimation, QEasingCurve,
    Property, Signal, QObject, QPointF
)
from PySide6.QtGui import (
    QColor, QPainter, QPen, QFont, QLinearGradient,
    QRadialGradient, QPainterPath, QBrush
)
from PySide6.QtWidgets import QWidget, QApplication, QGraphicsDropShadowEffect

from utils.logger import get_logger

logger = get_logger(__name__)

# ─── Design Tokens ──────────────────────────────────────────
PILL_WIDTH = 480
PILL_HEIGHT = 56
PILL_RADIUS = 28
MARGIN_TOP = 18

# Color palette
CYAN = QColor(0, 255, 255)
CYAN_DIM = QColor(0, 255, 255, 60)
CYAN_GLOW = QColor(0, 255, 255, 30)
BG_DARK = QColor(12, 12, 20, 220)
BG_GLASS = QColor(20, 20, 35, 200)
WHITE_DIM = QColor(255, 255, 255, 180)
GREEN_STATUS = QColor(0, 255, 120)
AMBER_STATUS = QColor(255, 180, 0)
RED_STATUS = QColor(255, 60, 60)


class OverlayState:
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    OBSERVING = "observing"


class JarvisOverlay(QWidget):
    """Transparent, always-on-top floating HUD pill bar."""

    def __init__(self, event_bus=None) -> None:
        super().__init__()
        self._events = event_bus
        self._state = OverlayState.IDLE
        self._status_text = "SYSTEM READY"
        self._phase = 0.0
        self._waveform = [0.0] * 32
        self._glow_alpha = 0.0
        self._drag_pos = None

        # Window setup — frameless, transparent, always on top
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool  # Hides from taskbar
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(PILL_WIDTH, PILL_HEIGHT)

        # Center at top of primary screen
        self._position_at_top()

        # Animation timer (60fps)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

        # Subscribe to events
        if self._events:
            self._events.subscribe("overlay_state", self._on_state_change)
            self._events.subscribe("command_result", self._on_command_result)

        # Drop shadow for depth
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 255, 255, 80))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    def _position_at_top(self) -> None:
        """Place the pill at the top-center of the primary screen."""
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + MARGIN_TOP
            self.move(x, y)

    # ─── State Management ──────────────────────────────────

    def set_state(self, state: str, text: str = "") -> None:
        self._state = state
        if text:
            self._status_text = text
        elif state == OverlayState.IDLE:
            self._status_text = "SYSTEM READY"
        elif state == OverlayState.LISTENING:
            self._status_text = "LISTENING..."
        elif state == OverlayState.THINKING:
            self._status_text = "ANALYZING..."
        elif state == OverlayState.SPEAKING:
            self._status_text = "SPEAKING"
        elif state == OverlayState.OBSERVING:
            self._status_text = "OBSERVING"

    def _on_state_change(self, payload: dict) -> None:
        state = payload.get("state", OverlayState.IDLE)
        text = payload.get("text", "")
        self.set_state(state, text)

    def _on_command_result(self, payload: dict) -> None:
        msg = payload.get("message", "")
        if msg:
            self.set_state(OverlayState.SPEAKING, msg[:40])
            QTimer.singleShot(3000, lambda: self.set_state(OverlayState.IDLE))
        else:
            self.set_state(OverlayState.IDLE)

    # ─── Animation Loop ───────────────────────────────────

    def _tick(self) -> None:
        self._phase += 0.04
        if self._phase > 2 * math.pi * 100:
            self._phase = 0

        # Generate waveform based on state
        if self._state == OverlayState.LISTENING:
            self._waveform = [
                0.3 + 0.7 * abs(math.sin(self._phase * 2 + i * 0.4))
                for i in range(32)
            ]
        elif self._state == OverlayState.THINKING:
            self._waveform = [
                0.1 + 0.3 * abs(math.sin(self._phase * 4 + i * 0.2))
                for i in range(32)
            ]
        elif self._state == OverlayState.SPEAKING:
            self._waveform = [
                0.2 + 0.8 * abs(math.sin(self._phase * 3 + i * 0.5)) * random.uniform(0.6, 1.0)
                for i in range(32)
            ]
        elif self._state == OverlayState.OBSERVING:
            self._waveform = [
                0.05 + 0.15 * abs(math.sin(self._phase + i * 0.3))
                for i in range(32)
            ]
        else:
            # Idle — subtle breathing
            self._waveform = [
                0.05 + 0.08 * abs(math.sin(self._phase * 0.5 + i * 0.2))
                for i in range(32)
            ]

        self.update()

    # ─── Painting ────────────────────────────────────────

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        w, h = self.width(), self.height()
        rect = QRectF(0, 0, w, h)

        # ── Background Pill ──────────────────────────────
        path = QPainterPath()
        path.addRoundedRect(rect.adjusted(2, 2, -2, -2), PILL_RADIUS, PILL_RADIUS)

        # Glass gradient
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, QColor(25, 25, 45, 210))
        grad.setColorAt(0.5, QColor(15, 15, 30, 230))
        grad.setColorAt(1, QColor(10, 10, 22, 240))
        painter.fillPath(path, QBrush(grad))

        # ── Border Glow ──────────────────────────────────
        border_color = self._state_color()
        glow_alpha = int(80 + 40 * abs(math.sin(self._phase)))
        border_color.setAlpha(glow_alpha)

        pen = QPen(border_color, 1.5)
        painter.setPen(pen)
        painter.drawPath(path)

        # ── Status Dot ───────────────────────────────────
        dot_color = self._state_color()
        dot_x = 22.0
        dot_y = h / 2
        dot_r = 4.0 + 1.0 * abs(math.sin(self._phase * 2))

        # Dot glow
        glow = QRadialGradient(QPointF(dot_x, dot_y), dot_r * 3)
        glow.setColorAt(0, QColor(dot_color.red(), dot_color.green(), dot_color.blue(), 60))
        glow.setColorAt(1, QColor(dot_color.red(), dot_color.green(), dot_color.blue(), 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(QPointF(dot_x, dot_y), dot_r * 3, dot_r * 3)

        # Solid dot
        painter.setBrush(QBrush(dot_color))
        painter.drawEllipse(QPointF(dot_x, dot_y), dot_r, dot_r)

        # ── "JARVIS" Label ───────────────────────────────
        painter.setPen(QColor(255, 255, 255, 200))
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.drawText(QRectF(36, 0, 70, h), Qt.AlignVCenter, "JARVIS")

        # ── Waveform Visualizer ──────────────────────────
        wave_start = 110.0
        wave_end = 320.0
        wave_width = wave_end - wave_start
        bar_count = len(self._waveform)
        bar_spacing = wave_width / bar_count
        bar_w = max(2.0, bar_spacing * 0.5)
        max_bar_h = h * 0.55

        wave_color = self._state_color()
        wave_color.setAlpha(180)

        for i, amp in enumerate(self._waveform):
            bar_h = max(2, amp * max_bar_h)
            bx = wave_start + i * bar_spacing
            by = (h - bar_h) / 2

            # Gradient per bar
            bar_grad = QLinearGradient(bx, by, bx, by + bar_h)
            c = self._state_color()
            bar_grad.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 200))
            bar_grad.setColorAt(0.5, QColor(c.red(), c.green(), c.blue(), 255))
            bar_grad.setColorAt(1, QColor(c.red(), c.green(), c.blue(), 200))

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(bar_grad))
            painter.drawRoundedRect(QRectF(bx, by, bar_w, bar_h), 1, 1)

        # ── Status Text ──────────────────────────────────
        painter.setPen(QColor(255, 255, 255, 160))
        painter.setFont(QFont("Segoe UI", 8))
        status_rect = QRectF(330, 0, w - 340, h)
        text = self._status_text[:30]
        painter.drawText(status_rect, Qt.AlignVCenter | Qt.AlignRight, text)

        painter.end()

    def _state_color(self) -> QColor:
        """Return the accent color for the current state."""
        if self._state == OverlayState.LISTENING:
            return QColor(0, 255, 255)       # Cyan
        elif self._state == OverlayState.THINKING:
            return QColor(160, 120, 255)      # Purple
        elif self._state == OverlayState.SPEAKING:
            return QColor(0, 255, 120)        # Green
        elif self._state == OverlayState.OBSERVING:
            return QColor(255, 180, 0)        # Amber
        else:
            return QColor(0, 255, 255, 120)   # Dim cyan

    # ─── Drag Support ────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos and event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event) -> None:
        """Double click to toggle visibility of the main window."""
        if self._events:
            self._events.emit("toggle_main_window")
