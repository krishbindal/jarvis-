"""
JARVIS-X Phase 27: Conversation Personality

Persistent user preferences stored via MemoryDB's knowledge table.
Jarvis learns your name, habits, and preferences over time.

Migrated from a separate 'preferences' table to the unified 'knowledge' table
via MemoryDB to eliminate dual-store inconsistency.
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
    # Migrate: ensure the old 'preferences' table data is moved to 'knowledge'
    try:
        conn.execute("SELECT 1 FROM preferences LIMIT 1")
        # Old table exists — migrate rows into knowledge
        conn.execute("""
            INSERT OR IGNORE INTO knowledge (key, value, category, updated_at)
            SELECT key, value, 'preference', updated_at FROM preferences
        """)
        conn.execute("DROP TABLE IF EXISTS preferences")
        conn.commit()
        logger.info("[PERSONALITY] Migrated preferences -> knowledge table.")
    except sqlite3.OperationalError:
        pass  # No old table — nothing to migrate
    return conn


def set_preference(key: str, value: str) -> None:
    """Store a user preference in the knowledge table."""
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO knowledge (key, value, category, updated_at) VALUES (?, ?, 'preference', datetime('now')) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
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
    """Retrieve a user preference from the knowledge table."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT value FROM knowledge WHERE key = ?", (key.lower(),)
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def get_all_preferences() -> Dict[str, str]:
    """Get all stored preferences from the knowledge table."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT key, value FROM knowledge WHERE category = 'preference' ORDER BY key"
        ).fetchall()
        return {k: v for k, v in rows}
    finally:
        conn.close()


def get_user_name() -> str:
    """Get the user's preferred name, or empty string if unknown."""
    return get_preference("user_name") or ""


def get_personality_context() -> str:
    """Build a personality context string for AI prompts, including user preferences and self-learned rules."""
    prefs = get_all_preferences()
    
    # Retrieve self-learned rules from the unified knowledge database
    rules = []
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT value FROM knowledge WHERE category = 'learned_rule' ORDER BY updated_at DESC LIMIT 5"
        ).fetchall()
        rules = [r[0] for r in rows]
    except Exception:
        pass
    finally:
        conn.close()

    lines = []
    if prefs:
        lines.append("USER PERSONALITY PROFILE:")
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

    if rules:
        if lines:
            lines.append("")
        lines.append("SELF-LEARNED BEHAVIORAL RULES (derived from your own self-reflection):")
        for rule in rules:
            lines.append(f"  - {rule}")

    return "\n".join(lines)


def run_self_reflection() -> Dict[str, Any]:
    """Jarvis reflects on its own recent performance to learn new rules and grow more capable."""
    try:
        from memory.database import MemoryDB
        db = MemoryDB()
        history = db.get_recent_history(15)
        if not history:
            return {
                "success": True,
                "status": "success",
                "message": "I've checked my memory logs. Since we haven't conversed much yet, I don't have enough data to run a self-reflection cycle. Let's talk more first!",
                "output": "no_history"
            }

        transcript = []
        for item in history:
            role = item.get("role", "user")
            content = item.get("content", "")
            if content:
                transcript.append(f"{role.upper()}: {content}")
        transcript_str = "\n".join(transcript)

        from brain.ai_engine import query_ai
        prompt = f"""
You are the self-reflection sub-agent for Jarvis, a sophisticated, capable desktop companion.
Analyze the following recent interaction history. Identify any repetitive phrasing, missed opportunities, or areas where your response could be more natural, concise, or helpful.

Output 1 to 3 specific, actionable rules or behavioral guidelines for yourself to improve future interactions.
Prefix each rule with "[LEARNED RULE]" on a new line. Do not output JSON or extra conversational wrapper.
If everything was optimal and no improvements are needed, output "NONE".

Recent History:
{transcript_str}
"""
        logger.info("[PERSONALITY] Initiating self-reflection cycle...")
        response = query_ai(prompt, system_msg="You are Jarvis reflecting on your own performance to grow more capable.")
        
        rules = []
        for line in response.splitlines():
            if "[LEARNED RULE]" in line:
                rule = line.split("[LEARNED RULE]", 1)[1].strip(" :*-\"")
                if len(rule) > 10:
                    rules.append(rule)
                    
        if not rules:
            return {
                "success": True,
                "status": "success",
                "message": "I've reviewed our recent interactions. All systems are performing optimally, and no self-corrections are required at this time.",
                "output": "all_optimal"
            }

        # Save rules to knowledge table
        conn = _get_conn()
        try:
            for rule in rules:
                key = f"learned_rule_{hash(rule) & 0xffffffff:x}"
                conn.execute(
                    "INSERT INTO knowledge (key, value, category, updated_at) VALUES (?, ?, 'learned_rule', datetime('now')) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                    (key, rule)
                )
            conn.commit()
        finally:
            conn.close()

        summary = "\n".join(f"  * {r}" for r in rules)
        logger.info("[PERSONALITY] Self-reflection completed. Learned rules:\n%s", summary)
        
        # personalized user greeting
        user_name = get_user_name()
        address = f"{user_name}, " if user_name else ""
        return {
            "success": True,
            "status": "success",
            "message": f"I've completed my self-reflection cycle and established new guidelines to refine my future actions:\n{summary}",
            "output": summary
        }
        
    except Exception as e:
        logger.error("[PERSONALITY] Self-reflection failed: %s", e)
        return {
            "success": False,
            "status": "error",
            "message": f"Self-reflection cycle encountered an issue: {e}",
            "output": str(e)
        }


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
