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
VOICE_MODEL_PATH = os.getenv("VOICE_MODEL_PATH", "voice/model")

# AI Models
MODEL_NAME = os.getenv("MODEL_NAME", "llama3")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Integrations and execution
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "https://your-n8n-url/webhook/jarvis")
SAFE_DIRECTORIES = [
    os.path.expanduser("~/Downloads"),
    os.path.expanduser("~/Desktop"),
    os.path.expanduser("~/Documents"),
    "C:/Users"
]
REQUEST_TIMEOUT = 10

# Communication (Gmail Defaults)
EMAIL_USER = os.getenv("EMAIL_USER", "your-email@gmail.com")
EMAIL_PASS = os.getenv("EMAIL_PASS", "")  # Use App Password
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
