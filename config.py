"""Configuration defaults for JARVIS-X Phase 1."""

# Clap detection
CLAP_THRESHOLD = 0.35
CLAP_MIN_GAP_S = 0.5
CLAP_MAX_GAP_S = 1.0
CLAP_COOLDOWN_S = 2.5
CLAP_CALIBRATION_S = 2.0

# Integrations and execution
N8N_WEBHOOK_URL = "https://your-n8n-url/webhook/jarvis"
SAFE_DIRECTORIES = ["C:/Users", "~/Downloads"]
MODEL_NAME = "llama3"
REQUEST_TIMEOUT = 10
