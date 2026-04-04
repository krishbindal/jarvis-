"""Comprehensive smoke test for JARVIS dynamic command router."""

from core.command_router import route_command

tests = [
    # ── USER TEST CASES ──────────────────────────────────────────────
    ("open youtube on chrome",       "open_dynamic",  "url"),
    ("open github.com in edge",      "open_dynamic",  "url"),
    ("open notes.txt in vscode",     "open_dynamic",  "file"),
    ("open downloads folder",        "open_folder",   None),
    ("open random query",            "open_app",      None),
    # ── GREETINGS ────────────────────────────────────────────────────
    ("hi",                           "chat",          None),
    ("hello",                        "chat",          None),
    ("how are you",                  "chat",          None),
    ("thanks",                       "chat",          None),
    ("good morning",                 "chat",          None),
    # ── FILLER STRIPPING ─────────────────────────────────────────────
    ("can you open youtube",         "open_dynamic",  None),
    ("could you open google.com",    "open_dynamic",  None),
    ("will you open chrome",         "open_app",      None),
    # ── NAVIGATION ───────────────────────────────────────────────────
    ("go to downloads",              "open_folder",   None),
    ("now go to downloads",          "open_folder",   None),
    ("take me to desktop",           "open_folder",   None),
    ("navigate to documents",        "open_folder",   None),
    # ── MEDIA ────────────────────────────────────────────────────────
    ("pause music",                  "media_control", None),
    ("play music",                   "media_control", None),
    ("skip this song",               "media_control", None),
    ("volume up",                    "media_control", None),
    ("mute",                         "media_control", None),
    # ── DYNAMIC URLS (no hardcoding) ─────────────────────────────────
    ("open instagram",               "open_dynamic",  None),
    ("open reddit.com",              "open_dynamic",  None),
    ("open stackoverflow",           "open_dynamic",  None),
    # ── SPECIFIC APP + TARGET ────────────────────────────────────────
    ("open report.pdf in notepad",   "open_dynamic",  None),
    ("open youtube in firefox",      "open_dynamic",  None),
    # ── POWER ────────────────────────────────────────────────────────
    ("lock computer",                "power_state",   None),
    # ── SEARCH ───────────────────────────────────────────────────────
    ("search for python tips",       "quick_search",  None),
    ("what is machine learning",     "quick_search",  None),
    # ── SCREEN ───────────────────────────────────────────────────────
    ("take screenshot",              "capture_screen", None),
]

print("=" * 70)
print("  JARVIS-X Universal Dynamic Router — Smoke Test")
print("=" * 70)
passed = 0
failed_list = []

for cmd, exp_action, exp_type in tests:
    r = route_command(cmd)
    got_action = r.get("action")
    ok = got_action == exp_action
    if ok:
        passed += 1
        status = "OK"
    else:
        status = "FAIL"
        failed_list.append((cmd, exp_action, got_action))

    extra_info = ""
    if r.get("extra"):
        app = r["extra"].get("app", "")
        rtype = r["extra"].get("resolved_type", "")
        if app:
            extra_info += f" app={app}"
        if rtype:
            extra_info += f" type={rtype}"

    print(f"  [{status}] {cmd!r:45s} -> {got_action!r:18s}{extra_info}")

print()
print(f"  Result: {passed}/{len(tests)} passed")

if failed_list:
    print()
    print("  FAILURES:")
    for cmd, exp, got in failed_list:
        print(f"    {cmd!r} — expected {exp!r} got {got!r}")
else:
    print("  ALL TESTS PASSED!")

print("=" * 70)
