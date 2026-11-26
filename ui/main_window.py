from __future__ import annotations

"""Jarvis-themed UI with command emission and logging."""

import os
import sys
from PySide6.QtCore import Qt, QTimer, QPoint, Signal, Slot, QObject
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
    QMessageBox,
)

from utils import EventBus
from utils.system_context import get_system_stats
from utils.logger import get_logger
import math

logger = get_logger(__name__)

# UI Constants
ACCENT = "#00ffff"
NEON_GLOW = "rgba(0, 255, 255, 120)"

class SignalBridge(QObject):
    """Bridge for thread-safe EventBus communication."""
    result_signal = Signal(dict)
    stream_signal = Signal(dict)
    cinematic_signal = Signal(dict)
    progress_signal = Signal(dict)
    approval_signal = Signal(dict)

class JarvisWindow(QMainWindow):
    """Modern, Glassmorphism-themed window for JARVIS-X."""

    def __init__(self, event_bus: EventBus) -> None:
        super().__init__()
        self._events = event_bus
        self.setWindowTitle("JARVIS-X")
        self.setMinimumSize(980, 700)
        self.resize(1180, 800)
        
        # Frameless and Transparent
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Signals Bridge (more robust for experimental PySide6/Python environments)
        self.signals = SignalBridge()
        self.signals.result_signal.connect(self._on_command_result)
        self.signals.stream_signal.connect(self._on_stream_output)
        self.signals.cinematic_signal.connect(self._on_cinematic_log)
        self.signals.progress_signal.connect(self._on_command_progress)
        self.signals.approval_signal.connect(self._on_action_approval)

        self._setup_glass_effect()
        self._build_layout()
        self._load_styles()

        if self._events:
            self._events.subscribe("command_result", self.signals.result_signal.emit)
            self._events.subscribe("stream_output", self.signals.stream_signal.emit)
            self._events.subscribe("cinematic_log", self.signals.cinematic_signal.emit)
            self._events.subscribe("command_progress", self.signals.progress_signal.emit)
            self._events.subscribe("action_approval_requested", self.signals.approval_signal.emit)
        self._drag_pos = QPoint()
        self._streaming = False
        self._typing_timer = QTimer(self)
        self._typing_timer.timeout.connect(self._type_tick)
        self._type_queue = []
        self._current_line = ""
        self._type_index = 0
        from core.action_policy import get_action_approvals
        get_action_approvals().set_ui_ready(True)

    def _setup_glass_effect(self) -> None:
        """Enable Windows 11 Acrylic effect if available."""
        try:
            from winmica import ApplyMica
            # Apply Mica/Acrylic to the HWND
            # We use try/except block to handle potential winId() or winmica issues
            hwnd = int(self.winId())
            ApplyMica(hwnd, dark_mode=True)
            logger.info("[UI] Windows 11 Mica effect applied.")
        except Exception as e:
            logger.debug("[UI] Failed to apply Mica effect (likely non-Win11 or missing lib): %s", e)

    def _load_styles(self) -> None:
        qss_path = os.path.join(os.path.dirname(__file__), "styles.qss")
        if os.path.exists(qss_path):
            with open(qss_path, "r") as f:
                self.setStyleSheet(f.read())

    def _build_layout(self) -> None:
        """Build a readable dashboard, without inventing connection/readiness data."""
        import config

        self.central = QWidget()
        self.central.setObjectName("CentralWidget")
        self.setCentralWidget(self.central)

        layout = QVBoxLayout(self.central)
        layout.setSpacing(14)
        layout.setContentsMargins(26, 22, 26, 22)

        # Header / drag area, with real window controls.
        header = QHBoxLayout()
        brand = QVBoxLayout()
        brand.setSpacing(2)
        self.title_label = QLabel("J A R V I S   /   X")
        self.title_label.setObjectName("Title")
        brand.addWidget(self.title_label)
        subtitle = QLabel("YOUR DESKTOP COPILOT   •   ACTIONS WITH ACCOUNTABILITY")
        subtitle.setObjectName("Subtitle")
        brand.addWidget(subtitle)
        header.addLayout(brand)
        header.addStretch()

        header_hint = QLabel("LOCAL SESSION")
        header_hint.setObjectName("HeaderHint")
        header.addWidget(header_hint)

        minimize = QPushButton("—")
        minimize.setObjectName("WindowControl")
        minimize.setToolTip("Minimize Jarvis")
        minimize.setFixedSize(36, 34)
        minimize.clicked.connect(self.showMinimized)
        header.addWidget(minimize)

        close_btn = QPushButton("×")
        close_btn.setObjectName("WindowClose")
        close_btn.setToolTip("Close Jarvis safely")
        close_btn.setFixedSize(36, 34)
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn)
        layout.addLayout(header)

        # Primary surface: system HUD and factual privacy / execution state.
        surface = QHBoxLayout()
        surface.setSpacing(14)

        hero = QFrame()
        hero.setObjectName("HeroPanel")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(20, 18, 20, 12)
        hero_layout.setSpacing(8)
        eyebrow = QLabel("01  /  MISSION CONTROL")
        eyebrow.setObjectName("Eyebrow")
        hero_layout.addWidget(eyebrow)

        self.status_label = QLabel("READY FOR COMMANDS")
        self.status_label.setObjectName("Status")
        self.status_label.setProperty("resultState", "ready")
        hero_layout.addWidget(self.status_label)

        status_note = QLabel("Execution status comes from actual tool responses, not AI narration.")
        status_note.setObjectName("Muted")
        status_note.setWordWrap(True)
        hero_layout.addWidget(status_note)

        self.hud = HUDWidget()
        self.hud.setMinimumHeight(170)
        hero_layout.addWidget(self.hud, stretch=1)
        surface.addWidget(hero, stretch=3)

        insights = QFrame()
        insights.setObjectName("InfoPanel")
        insights_layout = QVBoxLayout(insights)
        insights_layout.setContentsMargins(20, 18, 20, 18)
        insights_layout.setSpacing(11)
        meta = QLabel("02  /  TRUST & CONTROL")
        meta.setObjectName("Eyebrow")
        insights_layout.addWidget(meta)

        privacy_header = QLabel("DATA SHARING")
        privacy_header.setObjectName("InfoHeading")
        insights_layout.addWidget(privacy_header)
        privacy_items = (
            ("Cloud voice", config.ALLOW_CLOUD_STT),
            ("Cloud screen", config.ALLOW_CLOUD_VISION),
            ("Cloud clipboard", config.ALLOW_CLOUD_CLIPBOARD),
        )
        self.privacy_label = QLabel(
            "\\n".join(f"{name}: {'ON' if enabled else 'OFF'}" for name, enabled in privacy_items)
        )
        self.privacy_label.setObjectName("PrivacySummary")
        self.privacy_label.setWordWrap(True)
        insights_layout.addWidget(self.privacy_label)

        state_heading = QLabel("LAST EXECUTION")
        state_heading.setObjectName("InfoHeading")
        insights_layout.addWidget(state_heading)
        self.execution_label = QLabel("No actions executed in this session.")
        self.execution_label.setWordWrap(True)
        self.execution_label.setObjectName("ExecutionSummary")
        insights_layout.addWidget(self.execution_label)

        self.validation_label = QLabel(
            "Sensitive actions require your approval. A tool report is not independent verification."
        )
        self.validation_label.setObjectName("Muted")
        self.validation_label.setWordWrap(True)
        insights_layout.addWidget(self.validation_label)
        insights_layout.addStretch(1)
        surface.addWidget(insights, stretch=2)
        layout.addLayout(surface, stretch=5)

        activity_heading = QHBoxLayout()
        activity_title = QLabel("03  /  ACTIVITY TIMELINE")
        activity_title.setObjectName("Eyebrow")
        activity_heading.addWidget(activity_title)
        activity_heading.addStretch()
        activity_hint = QLabel("LATEST EVENTS  •  LOCAL DISPLAY")
        activity_hint.setObjectName("Muted")
        activity_heading.addWidget(activity_hint)
        layout.addLayout(activity_heading)

        self.console = QTextEdit()
        self.console.setObjectName("ActivityConsole")
        self.console.setReadOnly(True)
        self.console.setPlaceholderText("Ready to record actual command and execution events…")
        self.console.document().setMaximumBlockCount(500)
        layout.addWidget(self.console, stretch=3)

        composer = QFrame()
        composer.setObjectName("CommandPanel")
        composer_layout = QVBoxLayout(composer)
        composer_layout.setContentsMargins(16, 12, 16, 13)
        composer_layout.setSpacing(9)

        composer_title = QLabel("SEND A COMMAND")
        composer_title.setObjectName("Eyebrow")
        composer_layout.addWidget(composer_title)

        input_row = QHBoxLayout()
        input_row.setSpacing(9)
        self.command_input = QLineEdit()
        self.command_input.setObjectName("CommandInput")
        self.command_input.setPlaceholderText("Ask Jarvis to do a specific task…")
        self.command_input.setAccessibleName("Jarvis command")
        self.command_input.returnPressed.connect(self._emit_command)
        input_row.addWidget(self.command_input, stretch=1)

        talk = QPushButton("TALK")
        talk.setObjectName("SecondaryAction")
        talk.setToolTip("Listen for one command; requires a local Vosk model")
        talk.clicked.connect(lambda: self._events.emit("jarvis_wake", {"source": "app_internal"}))
        input_row.addWidget(talk)

        execute = QPushButton("RUN TASK")
        execute.setObjectName("PrimaryAction")
        execute.setCursor(Qt.PointingHandCursor)
        execute.clicked.connect(self._emit_command)
        input_row.addWidget(execute)

        stop_btn = QPushButton("STOP")
        stop_btn.setObjectName("StopAction")
        stop_btn.setToolTip("Request interruption and cancel pending approvals")
        stop_btn.clicked.connect(self._request_stop)
        input_row.addWidget(stop_btn)
        composer_layout.addLayout(input_row)

        suggestions = QHBoxLayout()
        suggestions.setSpacing(8)
        tip = QLabel("TRY")
        tip.setObjectName("Muted")
        suggestions.addWidget(tip)
        for prompt in ("system check", "open notepad", "list files"):
            button = QPushButton(prompt.title())
            button.setObjectName("Suggestion")
            button.setToolTip("Fill the command field; do not run automatically")
            button.clicked.connect(
                lambda checked=False, value=prompt: self._prefill_command(value)
            )
            suggestions.addWidget(button)
        suggestions.addStretch()
        composer_layout.addLayout(suggestions)
        layout.addWidget(composer)

        footer = QLabel(
            "JARVIS-X  /  ACTIONS REQUIRE EVIDENCE   •   CLOUD SHARING IS OPT-IN"
        )
        footer.setObjectName("Footer")
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)

    def _prefill_command(self, text: str) -> None:
        """Suggestions fill the field; no action occurs without another click."""
        self.command_input.setText(text)
        self.command_input.setFocus()

    def _request_stop(self) -> None:
        """Request cancellation, without falsely promising that external actions stopped."""
        from core.action_policy import get_action_approvals
        get_action_approvals().cancel_all()
        self._events.emit("interrupt_tts", {"source": "ui"})
        self._events.emit("interrupt_autonomy", {"source": "ui"})
        self.status_label.setText("INTERRUPT REQUESTED")
        self.execution_label.setText(
            "Cancellation requested. External actions already running may still finish."
        )
        self._append_log("SYSTEM > Stop requested; pending approvals cancelled.")

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    @Slot(dict)
    def _on_action_approval(self, payload: dict) -> None:
        """Show a real local user confirmation, never auto-approve LLM input."""
        from core.action_policy import get_action_approvals
        request_id = payload.get("request_id", "")
        action = str(payload.get("action", "unknown"))
        summary = str(payload.get("summary", ""))[:180]
        if not isinstance(request_id, str) or not request_id:
            return
        if not self.isVisible():
            self.show()
            self.raise_()
            self.activateWindow()

        box = QMessageBox(self)
        box.setWindowTitle("JARVIS — approval required")
        box.setIcon(QMessageBox.Icon.Warning)
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setText(
            f"Jarvis requests permission to perform:\n{action}\n\n"
            f"Target: {summary}\n\n"
            "Only approve if you intentionally asked for this specific action. "
            "If uncertain, choose No."
        )
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        approved = box.exec() == QMessageBox.StandardButton.Yes
        get_action_approvals().respond(request_id, approved)

    def closeEvent(self, event) -> None:
        from core.action_policy import get_action_approvals
        get_action_approvals().set_ui_ready(False)
        super().closeEvent(event)

    def _emit_command(self) -> None:
        text = self.command_input.text().strip()
        if not text:
            return
        self._append_log(f"USR > {text}")
        self.command_input.clear()
        self._events.emit("command_received", {"text": text})
        self.status_label.setText("WAITING FOR TOOL RESULTS")
        self.execution_label.setText("Command submitted; no action result has been confirmed yet.")

    @Slot(dict)
    def _on_command_result(self, payload: dict) -> None:
        """Render the executor's status, not an unverified AI completion claim."""
        message = str(payload.get("message") or "No execution result details.")[:500]
        status = str(payload.get("status") or "unverified").lower()
        reported_success = payload.get("success") is True
        if reported_success:
            label = "EXECUTOR REPORTED SUCCESS"
        elif payload.get("action") == "chat" and status == "unverified":
            label = "CHAT RESPONSE • NOT ACTION VERIFIED"
        elif status in ("busy", "interrupt_requested"):
            label = "ACTION WAITING / INTERRUPTED"
        else:
            label = "ATTENTION REQUIRED • NOT COMPLETED"
        self.status_label.setText(label)
        self.execution_label.setText(f"{status.upper()}: {message}")
        self._append_log(f"JARVIS [{status.upper()}] > {message}")
        self._streaming = False

    def _append_log(self, line: str) -> None:
        """Insert user/tool text literally, never as rich-text HTML."""
        cursor = self.console.textCursor()
        cursor.movePosition(QTextCursor.End)
        if not self.console.document().isEmpty():
            cursor.insertBlock()
        cursor.insertText(str(line)[:8000])
        self.console.setTextCursor(cursor)
        self.console.ensureCursorVisible()

    @Slot(dict)
    def _on_stream_output(self, payload: dict) -> None:
        token = payload.get("token", "")
        reset = payload.get("reset", False)
        if reset or not self._streaming:
            self._append_log("")
            self._streaming = True
        cursor = self.console.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(token)
        self.console.setTextCursor(cursor)

    @Slot(dict)
    def _on_cinematic_log(self, payload: dict) -> None:
        text = payload.get("text", "")
        if not text:
            return
        self._queue_type_line(text)

    @Slot(dict)
    def _on_command_progress(self, payload: dict) -> None:
        text = payload.get("text", "")
        if isinstance(text, str) and text:
            self.status_label.setText("RUNNING / " + text[:56].upper())
            self.execution_label.setText("Progress reported; final task status not yet confirmed.")
            self._queue_type_line(f"[STATUS] {text[:500]}")

    def _queue_type_line(self, text: str) -> None:
        text = str(text)[:500]
        if self._typing_timer.isActive():
            self._type_queue.append(text)
            return
        self._append_log("")
        self._current_line = text
        self._type_index = 0
        self._typing_timer.start(12)

    def _type_tick(self) -> None:
        if self._type_index >= len(self._current_line):
            self._typing_timer.stop()
            if self._type_queue:
                next_line = self._type_queue.pop(0)
                self._append_log("")
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
