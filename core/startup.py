from __future__ import annotations

import numpy as np
import sounddevice as sd

_SAMPLE_RATE = 44_100


def _generate_tone(duration_s: float = 2.5, start_freq: float = 220.0, end_freq: float = 660.0) -> np.ndarray:
    """Create a rising tone to emulate a cinematic startup."""
    samples = int(_SAMPLE_RATE * duration_s)
    time_axis = np.linspace(0.0, duration_s, samples, endpoint=False)
    frequencies = np.linspace(start_freq, end_freq, samples)
    phase = np.cumsum(2 * np.pi * frequencies / _SAMPLE_RATE)
    tone = 0.3 * np.sin(phase)
    fade_len = int(_SAMPLE_RATE * 0.35)
    fade = np.linspace(0.0, 1.0, fade_len)
    tone[:fade_len] *= fade
    tone[-fade_len:] *= fade[::-1]
    return tone.astype(np.float32)


def play_startup_sound() -> None:
    """Play a short tone; replace with Iron Man theme if available."""
    tone = _generate_tone()
    sd.play(tone, samplerate=_SAMPLE_RATE, blocking=True)
