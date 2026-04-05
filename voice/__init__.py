"""Voice integration package for Jarvis."""

# Re-export key modules so patches in tests (e.g., voice.tts_engine) resolve correctly.
from . import tts_engine  # noqa: F401
from . import voice_input  # noqa: F401
