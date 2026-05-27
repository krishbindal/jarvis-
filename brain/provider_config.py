"""Centralized AI provider configuration for JARVIS-X."""

# ── Model tiers ──────────────────────────────────────────────
FAST_MODEL = "llama-3.1-8b-instant"          # Quick narration, acks
PRIMARY_MODEL = "llama-3.1-8b-instant"       # Default light 8B model for fast command interpretation and planning
FALLBACK_MODEL = "llama-3.3-70b-versatile"    # Heavier 70B model for complex fallback only
GEMINI_MODEL = "gemini-2.0-flash"            # Fast, lightweight free tier cloud model

# ── Temperatures ─────────────────────────────────────────────
COMMAND_TEMP = 0.1       # Structured JSON — low creativity
CHAT_TEMP = 0.4          # Conversational — more natural
PLANNING_TEMP = 0.15     # Agent planning — slightly creative
QUERY_TEMP = 0.3         # General queries

# ── Timeouts (seconds) ───────────────────────────────────────
FAST_TIMEOUT = 5.0
NORMAL_TIMEOUT = 8.0
STREAM_TIMEOUT = 10.0

# ── Provider priority ────────────────────────────────────────
# Groq (ultra-fast cloud) -> Gemini (free cloud) -> Ollama (local last resort)
PROVIDER_ORDER = ["groq", "gemini", "ollama"]
