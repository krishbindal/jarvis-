"""
JARVIS-X Phase 27: Conversation Personality

Persistent user preferences stored in SQLite.
Jarvis learns your name, habits, and preferences over time.
"""

from __future__ import annotations

import sqlite3
import os
from typing import Any, Dict, Optional, List
from utils.logger import get_logger

logger = get_logger(__name__)

DB_PATH = os.path.join("memory", "jarvis.db")


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn


def set_preference(key: str, value: str) -> None:
    """Store a user preference."""
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO preferences (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (key.lower(), value)
        )
        conn.commit()
        logger.info("[PERSONALITY] Set: %s = %s", key, value)
    finally:
        conn.close()


def set_personality_handler(target: str) -> Dict[str, Any]:
    """Action handler for 'set_personality' tool. Target format: 'key:value'"""
    try:
        if ":" not in target:
            return {"success": False, "message": "Invalid personality format. Use 'key:value'"}
        
        key, value = target.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        
        # Mapping common terms to standardized keys
        key_map = {
            "name": "user_name",
            "hobby": "interests",
            "pref": "general_pref",
            "favorite": "favorites"
        }
        final_key = key_map.get(key, key)
        
        set_preference(final_key, value)
        return {
            "success": True, 
            "status": "success", 
            "message": f"I've updated my profile for you: {final_key} is now set to {value}.",
            "output": f"{final_key}:{value}"
        }
    except Exception as e:
        return {"success": False, "message": f"Failed to update personality: {e}"}


def get_preference(key: str) -> Optional[str]:
    """Retrieve a user preference."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT value FROM preferences WHERE key = ?", (key.lower(),)).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def get_all_preferences() -> Dict[str, str]:
    """Get all stored preferences."""
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT key, value FROM preferences ORDER BY key").fetchall()
        return {k: v for k, v in rows}
    finally:
        conn.close()


def get_personality_context() -> str:
    """Build a personality context string for AI prompts."""
    prefs = get_all_preferences()
    if not prefs:
        return ""

    lines = ["USER PERSONALITY PROFILE:"]
    pref_map = {
        "user_name": "Name",
        "nickname": "Preferred name",
        "tone": "Preferred tone",
        "expertise": "Technical level",
        "interests": "Interests",
        "work_hours": "Work hours",
        "fav_editor": "Favorite editor",
        "fav_browser": "Favorite browser",
        "fav_language": "Favorite language",
    }

    for key, label in pref_map.items():
        if key in prefs:
            lines.append(f"  - {label}: {prefs[key]}")

    # Include any extra custom preferences
    known_keys = set(pref_map.keys())
    for key, value in prefs.items():
        if key not in known_keys:
            lines.append(f"  - {key}: {value}")

    return "\n".join(lines)


def learn_from_interaction(user_input: str, ai_response: str) -> None:
    """Detect and store personality cues from natural conversation."""
    input_lower = user_input.lower()

    # Name detection
    for phrase in ["my name is ", "call me ", "i'm ", "i am "]:
        if phrase in input_lower:
            name = input_lower.split(phrase, 1)[1].split()[0].strip(".,!?").title()
            if len(name) > 1:
                set_preference("user_name", name)
                return

    # Preference detection
    pref_triggers = {
        "i prefer ": "general_pref",
        "i like ": "interests",
        "my favorite ": "favorites",
        "i use ": "tools",
        "i work with ": "tools",
    }

    for trigger, category in pref_triggers.items():
        if trigger in input_lower:
            value = input_lower.split(trigger, 1)[1].strip(".,!?")
            if len(value) > 2:
                existing = get_preference(category) or ""
                if value not in existing:
                    new_val = f"{existing}, {value}".strip(", ") if existing else value
                    set_preference(category, new_val)
                return
