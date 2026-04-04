from __future__ import annotations

"""Audio-based double-clap detector with ambient calibration."""

import threading
import time
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

import config
from utils import EventBus
from utils.logger import get_logger

logger = get_logger(__name__)


class ClapDetector:
    """Listens to the microphone and triggers on a double clap."""

    def __init__(
        self,
        on_double_clap: Optional[Callable[[], None]] = None,
        event_bus: Optional[EventBus] = None,
        event_name: str = "jarvis_wake",
        sample_rate: int = 44_100,
        chunk_size: int = 2_048,
        clap_threshold: float = config.CLAP_THRESHOLD,
        min_gap_s: float = config.CLAP_MIN_GAP_S,
        max_gap_s: float = config.CLAP_MAX_GAP_S,
        cooldown_s: float = config.CLAP_COOLDOWN_S,
        calibration_seconds: float = config.CLAP_CALIBRATION_S,
        device: Optional[int] = None,
    ) -> None:
        self.on_double_clap = on_double_clap
        self.event_bus = event_bus
        self.event_name = event_name
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.clap_threshold = clap_threshold
        self.min_gap_s = min_gap_s
        self.max_gap_s = max_gap_s
        self.cooldown_s = cooldown_s
        self.calibration_seconds = calibration_seconds
        self.device = device

        self._running = threading.Event()
        self._stream: Optional[sd.InputStream] = None
        self._first_clap_ts: Optional[float] = None
        self._last_trigger_ts: float = 0.0
        self._above_threshold = False
        self._calibration_done = False
        self._calibration_end_ts: float = 0.0
        self._noise_samples: list[float] = []
        self._noise_floor: float = 0.0
        self._dynamic_threshold: float = clap_threshold

    def start(self) -> None:
        if self._running.is_set():
            return
        self._calibration_done = False
        self._calibration_end_ts = time.monotonic() + self.calibration_seconds
        self._noise_samples = []
        self._noise_floor = 0.0
        self._dynamic_threshold = self.clap_threshold
        self._first_clap_ts = None
        self._last_trigger_ts = 0.0
        self._above_threshold = False
        print(f"Calibrating ambient noise for {self.calibration_seconds:.1f}s...")
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
        logger.info("Shutting down clap detector")
        self._running.clear()
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.error(f"Error stopping audio stream: {e}")
            finally:
                self._stream = None

    def _process_audio(self, indata: np.ndarray, frames: int, time_info, status) -> None:  # type: ignore[override]
        if status:
            print(f"Audio status: {status}")
        if not self._running.is_set():
            return

        now = time.monotonic()
        peak = float(np.max(np.abs(indata)))

        if not self._calibration_done:
            rms = float(np.sqrt(np.mean(np.square(indata))))
            self._noise_samples.append(rms)
            if now >= self._calibration_end_ts:
                if self._noise_samples:
                    self._noise_floor = float(np.median(self._noise_samples))
                self._dynamic_threshold = max(self.clap_threshold, self._noise_floor * 5.0, 0.05)
                self._calibration_done = True
                print(
                    f"Calibration complete. Noise floor={self._noise_floor:.4f}, "
                    f"threshold={self._dynamic_threshold:.4f}"
                )
            return

        threshold = self._dynamic_threshold
        if peak < threshold:
            self._above_threshold = False
            return

        if self._above_threshold:
            return
        self._above_threshold = True
        print(f"Peak detected: {peak:.3f} (threshold {threshold:.3f})")

        if now - self._last_trigger_ts < self.cooldown_s:
            print("Ignoring peak: in cooldown window.")
            return

        if self._first_clap_ts is None:
            self._first_clap_ts = now
            print("First clap candidate stored.")
            return

        delta = now - self._first_clap_ts
        if delta < self.min_gap_s:
            print(f"Ignoring peak: too close to first ({delta:.2f}s).")
            return
        if delta > self.max_gap_s:
            print(f"Resetting: peak too far from first ({delta:.2f}s).")
            self._first_clap_ts = now
            return

        self._trigger_double_clap(now, delta)
        self._first_clap_ts = None

    def _trigger_double_clap(self, ts: float, delta: float) -> None:
        self._last_trigger_ts = ts
        print(f"Double clap detected (gap {delta:.2f}s).")
        self._above_threshold = True
        if self.event_bus:
            self.event_bus.emit(self.event_name)
        if self.on_double_clap:
            try:
                self.on_double_clap()
            except Exception as exc:  # noqa: BLE001
                print(f"Clap callback failed: {exc}")
