"""Configuration defaults for JARVIS-X - Dexter Copilot."""

import os
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # noqa: BLE001
    def load_dotenv(*_args, **_kwargs):
        return False

# Load environment variables from .env file
load_dotenv()

# Clap detection
CLAP_THRESHOLD = 0.35
CLAP_MIN_GAP_S = 0.5
CLAP_MAX_GAP_S = 1.0
CLAP_COOLDOWN_S = 2.5
CLAP_CALIBRATION_S = 2.0

# Voice
WAKE_WORD = "jarvis"
VOICE_MODEL_PATH = os.getenv("VOICE_MODEL_PATH", "voice/model")

# AI Models
MODEL_NAME = os.getenv("MODEL_NAME", "llama3")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# n8n Integration
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/action")
N8N_NOTIFY_HOST = os.getenv("N8N_NOTIFY_HOST", "127.0.0.1")  # Loopback only by default
N8N_NOTIFY_PORT = int(os.getenv("N8N_NOTIFY_PORT", "5001"))  # Internal port for n8n to JARVIS communication
# Shared secret required to accept inbound notifications. Empty => server disabled.
N8N_NOTIFY_TOKEN = os.getenv("N8N_NOTIFY_TOKEN", "")

SAFE_DIRECTORIES = [
    os.path.expanduser("~/Downloads"),
    os.path.expanduser("~/Desktop"),
    os.path.expanduser("~/Documents"),
]
REQUEST_TIMEOUT = 10


def _env_flag(name: str, default: bool = False) -> bool:
    """Parse a boolean environment flag (1/true/yes/on)."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


# Security controls (opt-in for dangerous capabilities)
# When False, file operations are confined to SAFE_DIRECTORIES.
ALLOW_UNRESTRICTED_FS = _env_flag("JARVIS_ALLOW_UNRESTRICTED_FS", False)
# When False, LLM-generated / dynamic code is NOT executed automatically.
ALLOW_CODE_EXECUTION = _env_flag("JARVIS_ALLOW_CODE_EXECUTION", False)
# When False, clipboard contents are not sent to cloud LLMs.
ENABLE_CLIPBOARD_MONITOR = _env_flag("JARVIS_ENABLE_CLIPBOARD_MONITOR", False)
# When False, auto pip-install of missing modules is disabled.
ALLOW_AUTO_PIP = _env_flag("JARVIS_ALLOW_AUTO_PIP", False)

# Downloads
DOWNLOAD_DIR = os.getenv("JARVIS_DOWNLOAD_DIR", os.path.expanduser("~/Downloads"))
MAX_DOWNLOAD_BYTES = int(os.getenv("JARVIS_MAX_DOWNLOAD_BYTES", str(500 * 1024 * 1024)))  # 500 MB

# Communication (Gmail Defaults)
EMAIL_USER = os.getenv("EMAIL_USER", "your-email@gmail.com")
EMAIL_PASS = os.getenv("EMAIL_PASS", "")  # Use App Password
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
