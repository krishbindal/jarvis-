"""Configuration defaults for JARVIS-X upgraded architecture."""

# Clap detection
CLAP_THRESHOLD = 0.35
CLAP_MIN_GAP_S = 0.5
CLAP_MAX_GAP_S = 1.0
CLAP_COOLDOWN_S = 2.5
CLAP_CALIBRATION_S = 2.0

# Voice
VOICE_MODEL_PATH = "voice/model"
WAKE_WORD = "jarvis"
REQUIRE_WAKE_WORD = True

# Integrations and execution
N8N_WEBHOOK_URL = "https://your-n8n-url/webhook/jarvis"
SAFE_DIRECTORIES = ["C:/Users", "~/Downloads"]
MODEL_NAME = "llama3"
REQUEST_TIMEOUT = 10

# Intent and routing
INTENT_CONFIDENCE_THRESHOLD = 0.5
AI_COMPLEXITY_THRESHOLD = 0.55
MAX_HISTORY_ENTRIES = 5
MAX_RELEVANT_ENTRIES = 3

# Caching and workflows
RESPONSE_CACHE_PATH = "memory/response_cache.json"
RESPONSE_CACHE_TTL_S = 60 * 60
MACRO_PATH = "macros.json"
WORKFLOW_MEMORY_PATH = "memory/workflows.json"

# AI backends
REMOTE_MODEL_NAME = "gemini-1.5-flash"
REMOTE_AI_TIMEOUT = 15

# Background agent
BACKGROUND_POLL_S = 45
BACKGROUND_SUGGESTION_LIMIT = 3

# Execution safety
MAX_RETRY_ATTEMPTS = 2
