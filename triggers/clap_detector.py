from __future__ import annotations

import threading
import time
from typing import Callable, Optional

import numpy as np
import sounddevice as sd


class ClapDetector:
    """Listens to the microphone and triggers on a double clap."""

    def __init__(
        self,
        on_double_clap: Optional[Callable[[], None]] = None,
        sample_rate: int = 44_100,
        chunk_size: int = 2_048,
        clap_threshold: float = 0.35,
        max_gap_s: float = 0.45,
        cooldown_s: float = 1.5,
        device: Optional[int] = None,
    ) -> None:
        self.on_double_clap = on_double_clap
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.clap_threshold = clap_threshold
        self.max_gap_s = max_gap_s
        self.cooldown_s = cooldown_s
        self.device = device

        self._running = threading.Event()
        self._stream: Optional[sd.InputStream] = None
        self._first_clap_ts: Optional[float] = None
        self._last_trigger_ts: float = 0.0

    def start(self) -> None:
        if self._running.is_set():
            return
        try:
            stream = sd.InputStream(
                samplerate=self.sample_rate,
                blocksize=self.chunk_size,
                channels=1,
                dtype="float32",
                device=self.device,
                callback=self._process_audio,
            )
            stream.start()
        except Exception as exc:  # noqa: BLE001
            print(f"Unable to start clap detector: {exc}")
            self._running.clear()
            return

        self._stream = stream
        self._running.set()

    def stop(self) -> None:
        if self._stream is None:
            self._running.clear()
            return
        self._running.clear()
        try:
            self._stream.stop()
            self._stream.close()
        finally:
            self._stream = None

    def _process_audio(self, indata: np.ndarray, frames: int, time_info, status) -> None:  # type: ignore[override]
        if status:
            print(f"Audio status: {status}")
        if not self._running.is_set():
            return

        now = time.monotonic()
        peak = float(np.max(np.abs(indata)))
        if peak < self.clap_threshold:
            return

        if self._first_clap_ts and (now - self._first_clap_ts) <= self.max_gap_s:
            if now - self._last_trigger_ts < self.cooldown_s:
                return
            self._trigger_double_clap(now)
            self._first_clap_ts = None
            return

        self._first_clap_ts = now

    def _trigger_double_clap(self, ts: float) -> None:
        self._last_trigger_ts = ts
        print("Double clap detected.")
        if self.on_double_clap:
            try:
                self.on_double_clap()
            except Exception as exc:  # noqa: BLE001
                print(f"Clap callback failed: {exc}")
