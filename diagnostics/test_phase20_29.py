"""Smoke test for all Phase 20-29 modules."""
import os
import sys
import unittest

if os.environ.get("RUN_JARVIS_DIAGNOSTICS") != "1":
    raise unittest.SkipTest("Manual diagnostics suite; set RUN_JARVIS_DIAGNOSTICS=1 to run.")

tests = []

try:
    from triggers.wake_word import WakeWordDetector
    tests.append("WakeWord OK")
except Exception as e:
    tests.append(f"WakeWord FAIL: {e}")

try:
    from triggers.clipboard_monitor import ClipboardMonitor
    tests.append("Clipboard OK")
except Exception as e:
    tests.append(f"Clipboard FAIL: {e}")

try:
    from memory.personality import get_personality_context, learn_from_interaction
    tests.append("Personality OK")
except Exception as e:
    tests.append(f"Personality FAIL: {e}")

try:
    from skills import list_skills
    skills = list_skills()
    names = [s["name"] for s in skills]
    tests.append(f"Skills OK: {names}")
except Exception as e:
    tests.append(f"Skills FAIL: {e}")

try:
    from utils.notifications import notify
    tests.append("Notifications OK")
except Exception as e:
    tests.append(f"Notifications FAIL: {e}")

try:
    from skills.browser_agent import execute as browser_exec
    tests.append("Browser Agent OK")
except Exception as e:
    tests.append(f"Browser Agent FAIL: {e}")

try:
    from skills.music_player import execute as music_exec
    tests.append("Music Player OK")
except Exception as e:
    tests.append(f"Music Player FAIL: {e}")

try:
    from skills.code_buddy import execute as code_exec
    tests.append("Code Buddy OK")
except Exception as e:
    tests.append(f"Code Buddy FAIL: {e}")

try:
    from skills.reminder import execute as reminder_exec
    tests.append("Reminder OK")
except Exception as e:
    tests.append(f"Reminder FAIL: {e}")

try:
    from brain.vision_provider import get_vision_provider
    tests.append("Vision (multi-monitor) OK")
except Exception as e:
    tests.append(f"Vision FAIL: {e}")

print("\n".join(tests))
failed = sum(1 for t in tests if "FAIL" in t)
print(f"\n{'='*40}")
print(f"Results: {len(tests) - failed}/{len(tests)} passed")
if failed:
    sys.exit(1)
print("ALL MODULES PASSED")
