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
from PySide6.QtWidgets import QWidget, QApplication

from utils.logger import get_logger

logger = get_logger(__name__)

# ─── Design Tokens ──────────────────────────────────────────
# Increased dimensions to prevent shadow clipping
OVERLAY_WIDTH = 800
OVERLAY_HEIGHT = 180
PILL_WIDTH = 480
PILL_HEIGHT = 56
PILL_RADIUS = 28
MARGIN_TOP = 20

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
        self._target_waveform = [0.0] * 32
        self._drag_pos = None

        # Window setup — frameless, transparent, always on top
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(OVERLAY_WIDTH, OVERLAY_HEIGHT)

        self._position_at_top()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40) # 25 FPS – Better for low-end PCs

        if self._events:
            self._events.subscribe("overlay_state", self._on_state_change)
            self._events.subscribe("command_result", self._on_command_result)
            self._events.subscribe("proactive_notification", self._on_proactive_notification)
            self._events.subscribe("command_progress", self._on_command_progress)

    def _position_at_top(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + MARGIN_TOP
            self.move(x, y)

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

    def _on_command_progress(self, payload: dict) -> None:
        text = payload.get("text", "")
        if text:
            self.set_state(self._state, text[:40])

    def _tick(self) -> None:
        self._phase += 0.08 # Increased speed to match lower FPS
        if self._phase > 2 * math.pi * 100:
            self._phase = 0

        if self._state == OverlayState.LISTENING:
            self._target_waveform = [0.3 + 0.7 * abs(math.sin(self._phase * 2 + i * 0.4)) for i in range(32)]
        elif self._state == OverlayState.THINKING:
            self._target_waveform = [0.1 + 0.3 * abs(math.sin(self._phase * 4 + i * 0.2)) for i in range(32)]
        elif self._state == OverlayState.SPEAKING:
            self._target_waveform = [0.2 + 0.8 * abs(math.sin(self._phase * 3 + i * 0.5)) * random.uniform(0.6, 1.0) for i in range(32)]
        elif self._state == OverlayState.OBSERVING:
            self._target_waveform = [0.05 + 0.15 * abs(math.sin(self._phase + i * 0.3)) for i in range(32)]
        else:
            self._target_waveform = [0.05 + 0.08 * abs(math.sin(self._phase * 0.5 + i * 0.2)) for i in range(32)]

        for i in range(32):
            self._waveform[i] += (self._target_waveform[i] - self._waveform[i]) * 0.4

        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        # Performance: Only paint within window bounds
        painter.setClipRect(self.rect())
        
        w, h = self.width(), self.height()
        offset_x = (w - PILL_WIDTH) / 2
        offset_y = (h - PILL_HEIGHT) / 2
        rect = QRectF(offset_x, offset_y, PILL_WIDTH, PILL_HEIGHT)

        # ── Manual Shadow/Glow (Phase 17) ────────────────
        # Prevents UpdateLayeredWindowIndirect errors by keeping paint ops within window rect
        shadow_rect = rect.adjusted(-40, -40, 40, 40)
        glow = QRadialGradient(shadow_rect.center(), shadow_rect.width() / 2)
        accent = self._state_color()
        glow.setColorAt(0, QColor(accent.red(), accent.green(), accent.blue(), 40))
        glow.setColorAt(0.7, QColor(accent.red(), accent.green(), accent.blue(), 10))
        glow.setColorAt(1, Qt.transparent)
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(shadow_rect)

        # ── Background Pill ──────────────────────────────
        path = QPainterPath()
        path.addRoundedRect(rect.adjusted(2, 2, -2, -2), PILL_RADIUS, PILL_RADIUS)

        grad = QLinearGradient(0, offset_y, 0, offset_y + PILL_HEIGHT)
        grad.setColorAt(0, QColor(25, 25, 45, 210))
        grad.setColorAt(0.5, QColor(15, 15, 30, 230))
        grad.setColorAt(1, QColor(10, 10, 22, 240))
        painter.fillPath(path, QBrush(grad))

        # ── Border Glow ──────────────────────────────────
        border_color = self._state_color()
        border_color.setAlpha(int(80 + 40 * abs(math.sin(self._phase))))
        painter.setPen(QPen(border_color, 1.5))
        painter.drawPath(path)

        # ── Status Dot ───────────────────────────────────
        dot_x = offset_x + 22.0
        dot_y = h / 2
        dot_r = 4.0 + 1.0 * abs(math.sin(self._phase * 2))
        
        dot_glow = QRadialGradient(QPointF(dot_x, dot_y), dot_r * 3)
        dot_glow.setColorAt(0, QColor(accent.red(), accent.green(), accent.blue(), 60))
        dot_glow.setColorAt(1, Qt.transparent)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(dot_glow))
        painter.drawEllipse(QPointF(dot_x, dot_y), dot_r * 3, dot_r * 3)

        painter.setBrush(QBrush(accent))
        painter.drawEllipse(QPointF(dot_x, dot_y), dot_r, dot_r)

        # ── Labels & Text ───────────────────────────────
        painter.setPen(QColor(255, 255, 255, 200))
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.drawText(QRectF(offset_x + 36, offset_y, 70, PILL_HEIGHT), Qt.AlignVCenter, "JARVIS")

        # ── Waveform ─────────────────────────────────────
        wave_start = offset_x + 110.0
        bar_count = len(self._waveform)
        bar_spacing = 210.0 / bar_count
        bar_w = max(2.0, bar_spacing * 0.5)
        max_bar_h = PILL_HEIGHT * 0.55

        for i, amp in enumerate(self._waveform):
            bar_h = max(2, amp * max_bar_h)
            bx = wave_start + i * bar_spacing
            by = offset_y + (PILL_HEIGHT - bar_h) / 2
            
            bar_grad = QLinearGradient(bx, by, bx, by + bar_h)
            bar_grad.setColorAt(0, QColor(accent.red(), accent.green(), accent.blue(), 200))
            bar_grad.setColorAt(1, QColor(accent.red(), accent.green(), accent.blue(), 255))
            
            painter.setBrush(QBrush(bar_grad))
            painter.drawRoundedRect(QRectF(bx, by, bar_w, bar_h), 1, 1)

        painter.setPen(QColor(255, 255, 255, 160))
        painter.setFont(QFont("Segoe UI", 8))
        status_rect = QRectF(offset_x + 330, offset_y, PILL_WIDTH - 340, PILL_HEIGHT)
        painter.drawText(status_rect, Qt.AlignVCenter | Qt.AlignRight, self._status_text[:40])


        # ── Proactive Notification Bubble ────────────────
        if hasattr(self, '_proactive_text') and self._proactive_text:
            bubble_y = offset_y + PILL_HEIGHT + 10
            painter.setPen(QColor(255, 180, 0, 200)) # observing accent color
            painter.setFont(QFont("Segoe UI", 10, QFont.Medium))
            painter.drawText(QRectF(offset_x, bubble_y, PILL_WIDTH, 40), Qt.AlignCenter | Qt.TextWordWrap, self._proactive_text)

        painter.end()

    def _on_proactive_notification(self, payload: dict) -> None:
        self._proactive_text = payload.get("message", "")
        self.set_state(OverlayState.OBSERVING)
        
        # Clear after 8 seconds
        QTimer.singleShot(8000, self._clear_proactive_notification)

    def _clear_proactive_notification(self) -> None:
        self._proactive_text = ""
        self.set_state(OverlayState.IDLE)

    def _state_color(self) -> QColor:
        if self._state == OverlayState.LISTENING: return QColor(0, 255, 255)
        if self._state == OverlayState.THINKING: return QColor(160, 120, 255)
        if self._state == OverlayState.SPEAKING: return QColor(0, 255, 120)
        if self._state == OverlayState.OBSERVING: return QColor(255, 180, 0)
        return QColor(0, 255, 255, 120)

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
        if self._events:
            self._events.emit("toggle_main_window")
