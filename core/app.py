from __future__ import annotations

"""Application orchestration for JARVIS-X."""

import threading
import time
from typing import Optional

from core.command_router import route_command
from core.startup import start_startup_sequence
from executor.download_executor import download_file, download_video
from executor.conversion_executor import execute_conversion
from executor.system_executor import execute_file_command
from triggers.clap_detector import ClapDetector
from ui.application import launch_ui
from utils import EventBus


class JarvisApp:
    """Main application controller for JARVIS-X."""

    def __init__(self, auto_start: bool = False) -> None:
        self.auto_start = auto_start
        self._activation_event = threading.Event()
        self._events = EventBus()
        self._events.subscribe("jarvis_wake", self._handle_activation)
        self._events.subscribe("command_received", self._handle_command)
        self._clap_detector = ClapDetector(event_bus=self._events)
        self._listener_thread: Optional[threading.Thread] = None

    def _handle_activation(self) -> None:
        if self._activation_event.is_set():
            return
        print("Double clap detected. Preparing cinematic startup...")
        self._activation_event.set()
        self._clap_detector.stop()

    def _start_clap_listener(self) -> None:
        def _runner() -> None:
            try:
                self._clap_detector.start()
            except Exception as exc:  # noqa: BLE001
                print(f"Clap detector failed: {exc}")

        self._listener_thread = threading.Thread(target=_runner, name="clap-listener", daemon=True)
        self._listener_thread.start()

    def run(self) -> None:
        """Start the assistant and wait for activation."""
        try:
            if self.auto_start:
                self._activation_event.set()
            else:
                print("Listening for a double clap to start JARVIS-X...")
                self._start_clap_listener()

            self._activation_event.wait()
            self._start_cinematic_sequence()
        except KeyboardInterrupt:
            print("Shutting down...")
        finally:
            self._shutdown()

    def _start_cinematic_sequence(self) -> None:
        start_ts = time.monotonic()
        audio_thread = start_startup_sequence()
        try:
            launch_ui(self._events)
        except Exception as exc:  # noqa: BLE001
            print(f"UI launch failed: {exc}")
        if audio_thread and audio_thread.is_alive():
            audio_thread.join(timeout=0)
        end_ts = time.monotonic()
        print(f"Cinematic startup completed in {end_ts - start_ts:.2f}s")

    def _handle_command(self, payload: dict) -> None:
        try:
            text = payload.get("text", "")
            result = route_command(text)
            if result.get("type") == "file":
                exec_result = execute_file_command(result.get("action", ""), result.get("target", ""), result.get("extra", {}))
                result["exec_result"] = exec_result
                result["message"] = exec_result.get("message", result.get("message", ""))
            elif result.get("type") == "network":
                exec_result = download_file(result.get("target", ""))
                result["exec_result"] = exec_result
                result["message"] = exec_result.get("message", result.get("message", ""))
            elif result.get("type") == "conversion":
                exec_result = execute_conversion(result.get("action", ""), result.get("target", ""))
                result["exec_result"] = exec_result
                result["message"] = exec_result.get("message", result.get("message", ""))
            self._events.emit("command_result", result)
        except Exception as exc:  # noqa: BLE001
            print(f"Command handling failed: {exc}")

    def _shutdown(self) -> None:
        try:
            self._clap_detector.stop()
        finally:
            if self._listener_thread and self._listener_thread.is_alive():
                self._listener_thread.join(timeout=0.2)
