from __future__ import annotations

import threading
import time

from core.startup import play_startup_sound
from triggers.clap_detector import ClapDetector
from ui.application import launch_ui


class JarvisApp:
    """Main application controller for JARVIS-X."""

    def __init__(self, auto_start: bool = False) -> None:
        self.auto_start = auto_start
        self._activation_event = threading.Event()
        self._clap_detector = ClapDetector(on_double_clap=self._handle_activation)

    def _handle_activation(self) -> None:
        if self._activation_event.is_set():
            return
        print("Double clap detected. Preparing cinematic startup...")
        self._activation_event.set()
        self._clap_detector.stop()

    def run(self) -> None:
        """Start the assistant and wait for activation."""
        try:
            if self.auto_start:
                self._activation_event.set()
            else:
                print("Listening for a double clap to start JARVIS-X...")
                self._clap_detector.start()

            self._activation_event.wait()
            self._start_cinematic_sequence()
        except KeyboardInterrupt:
            print("Shutting down...")
        finally:
            self._clap_detector.stop()

    def _start_cinematic_sequence(self) -> None:
        start_ts = time.monotonic()
        try:
            play_startup_sound()
        except Exception as exc:  # noqa: BLE001
            print(f"Unable to play startup sound: {exc}")
        launch_ui()
        end_ts = time.monotonic()
        print(f"Cinematic startup completed in {end_ts - start_ts:.2f}s")
