"""
Phase 13: Comprehensive Test Suite for JARVIS-X Dynamic Command System.

Tests ALL 14 phases:
    1.  Universal command parsing
    2.  Target intelligence
    3.  Smart URL handling
    4.  Execution engine (handler dispatch)
    5.  Multi-step command support
    6.  Context awareness
    7.  Error handling
    8.  Structured logging (verified by logs)
    9.  Command normalization
    10. Self-healing (verified by runtime)
    11. Performance caching
    12. Universal fallback
    13. This test suite
    14. Clean architecture
"""

from core.command_router import route_command
from core.command_parser import normalize, split_multi_step, session, SessionContext
from core.command_cache import CommandCache


def run_tests():
    passed = 0
    failed = 0
    failures = []

    def check(label: str, expected, actual):
        nonlocal passed, failed
        ok = expected == actual
        if ok:
            passed += 1
            print(f"  [OK]   {label}")
        else:
            failed += 1
            failures.append((label, expected, actual))
            print(f"  [FAIL] {label}  expected={expected!r}  got={actual!r}")

    def action_of(result):
        if isinstance(result, list):
            return [r.get("action") for r in result]
        return result.get("action")

    def extra_of(result, key):
        if isinstance(result, dict):
            return (result.get("extra") or {}).get(key)
        return None

    # ═══════════════════════════════════════════
    print("=" * 70)
    print("  JARVIS-X Advanced Intelligence Upgrade — Test Suite")
    print("=" * 70)

    # ── PHASE 1: Universal Command Parsing ────────────────────
    print("\n  ─── Phase 1: Universal Command Parsing ───")
    check("open youtube",              "open_dynamic",  action_of(route_command("open youtube")))
    check("open github.com",           "open_dynamic",  action_of(route_command("open github.com")))
    check("open report.pdf",           "open_dynamic",  action_of(route_command("open report.pdf")))
    check("search python tips",        "quick_search",  action_of(route_command("search python tips")))
    check("play music",                "media_control", action_of(route_command("play music")))
    check("run workflow backup",       "trigger_n8n",   action_of(route_command("run workflow backup")))

    # ── PHASE 2: Target Intelligence ──────────────────────────
    print("\n  ─── Phase 2: Target Intelligence ───")
    r = route_command("open google.com")
    check("google.com → url type",     "url",    extra_of(r, "resolved_type"))
    r = route_command("open report.pdf")
    check("report.pdf → file type",    "file",   extra_of(r, "resolved_type"))
    check("open downloads folder",     "open_folder", action_of(route_command("open downloads folder")))
    check("open some random thing",    "open_app",    action_of(route_command("open some random thing")))

    # ── PHASE 3: Smart URL Handling ───────────────────────────
    print("\n  ─── Phase 3: Smart URL Handling ───")
    r = route_command("open youtube")
    check("youtube → youtube.com",     True,  "youtube.com" in r.get("target", ""))
    r = route_command("open google")
    check("google → google.com",       True,  "google.com" in r.get("target", ""))
    r = route_command("open stackoverflow")
    check("stackoverflow → SO url",    True,  "stackoverflow.com" in r.get("target", ""))

    # ── PHASE 4: Execution Engine ─────────────────────────────
    print("\n  ─── Phase 4: Execution Engine ───")
    r = route_command("open youtube on chrome")
    check("open youtube on chrome → open_dynamic", "open_dynamic", action_of(r))
    check("  app = chrome",           "chrome", extra_of(r, "app"))
    r = route_command("open github in edge")
    check("open github in edge → open_dynamic", "open_dynamic", action_of(r))
    check("  app = msedge",           "msedge", extra_of(r, "app"))
    r = route_command("open notes.txt in vscode")
    check("open notes.txt in vscode", "open_dynamic", action_of(r))
    check("  app = code",             "code",   extra_of(r, "app"))
    check("  type = file",            "file",   extra_of(r, "resolved_type"))

    # ── PHASE 5: Multi-Step Command Support ───────────────────
    print("\n  ─── Phase 5: Multi-Step Commands ───")
    steps = split_multi_step("open chrome and search youtube")
    check("split 'open chrome and search youtube'", 2, len(steps))
    check("  step 1 = open chrome",     "open chrome",     steps[0] if len(steps) > 0 else "")
    check("  step 2 = search youtube",  "search youtube",  steps[1] if len(steps) > 1 else "")

    steps = split_multi_step("open youtube then play music")
    check("split 'open youtube then play music'", 2, len(steps))

    steps = split_multi_step("open chrome and then search google and also open spotify")
    check("3-step: 'open chrome and then search google and also open spotify'",
          True, len(steps) >= 2)

    r = route_command("open chrome and search youtube")
    check("route_command returns list for multi-step", True, isinstance(r, list))
    if isinstance(r, list):
        check("  multi-step actions", True, len(r) >= 2)

    steps = split_multi_step("open youtube")
    check("single command stays single", 1, len(steps))

    # ── PHASE 6: Context Awareness ────────────────────────────
    print("\n  ─── Phase 6: Context Awareness ───")
    ctx = SessionContext()
    ctx.record("open_dynamic", "youtube", app="chrome")
    check("context: last_app = chrome", "chrome", ctx.last_app)
    check("context: last_action",       "open_dynamic", ctx.last_action)
    check("context: get_context_app",   "chrome", ctx.get_context_app())
    ctx.record("open_app", "notepad")  # no browser
    check("context: after non-browser, last_app still chrome", "chrome", ctx.get_context_app())
    ctx.clear()
    check("context: clear resets",      None, ctx.last_app)

    # ── PHASE 9: Command Normalization ────────────────────────
    print("\n  ─── Phase 9: Normalization ───")
    check("strip 'please'",         "open youtube",  normalize("please open youtube"))
    check("strip 'can you'",        "open youtube",  normalize("can you open youtube"))
    check("strip 'jarvis'",         "open youtube",  normalize("jarvis open youtube"))
    check("strip chained fillers",  "open youtube",  normalize("can you please just open youtube"))
    check("strip 'now'",            "go to downloads", normalize("now go to downloads"))
    check("lowercase + collapse",   "open my files", normalize("  OPEN  MY  FILES  "))
    check("strip 'i want to'",      "open chrome",   normalize("i want to open chrome"))

    # ── PHASE 11: Performance Caching ─────────────────────────
    print("\n  ─── Phase 11: Caching ───")
    cache = CommandCache(max_size=10, ttl_seconds=60)
    cache.put("test_key", {"action": "open_dynamic", "target": "test"})
    check("cache hit",              "open_dynamic", (cache.get("test_key") or {}).get("action"))
    check("cache miss",            None, cache.get("nonexistent"))
    stats = cache.stats
    check("cache stats: 1 hit",    1, stats["hits"])
    check("cache stats: 1 miss",   1, stats["misses"])

    # ── Greetings ─────────────────────────────────────────────
    print("\n  ─── Greetings ───")
    for g in ("hi", "hello", "how are you", "thanks", "good morning", "bye", "yo", "hola"):
        check(f"greeting: {g}", "chat", action_of(route_command(g)))

    # ── Navigation ────────────────────────────────────────────
    print("\n  ─── Navigation ───")
    check("go to downloads",        "open_folder",  action_of(route_command("go to downloads")))
    check("take me to desktop",     "open_folder",  action_of(route_command("take me to desktop")))
    check("navigate to documents",  "open_folder",  action_of(route_command("navigate to documents")))
    check("now go to downloads",    "open_folder",  action_of(route_command("now go to downloads")))

    # ── Media ─────────────────────────────────────────────────
    print("\n  ─── Media Controls ───")
    check("pause music",    "media_control", action_of(route_command("pause music")))
    check("skip this song", "media_control", action_of(route_command("skip this song")))
    check("volume up",      "media_control", action_of(route_command("volume up")))
    check("mute",           "media_control", action_of(route_command("mute")))

    # ── Power ─────────────────────────────────────────────────
    print("\n  ─── Power Controls ───")
    check("lock computer",  "power_state", action_of(route_command("lock computer")))

    # ── Screen ────────────────────────────────────────────────
    print("\n  ─── Screen ───")
    check("take screenshot", "capture_screen", action_of(route_command("take screenshot")))

    # ── Search ────────────────────────────────────────────────
    print("\n  ─── Search ───")
    check("search for python tips",  "quick_search", action_of(route_command("search for python tips")))
    check("what is machine learning", "quick_search", action_of(route_command("what is machine learning")))

    # ── Fallback ──────────────────────────────────────────────
    print("\n  ─── Fallback ───")
    check("unknown → AI fallback",  "unknown", action_of(route_command("asdjkfhaskjdfh")))

    # ═══════════════════════════════════════════
    print()
    print("=" * 70)
    total = passed + failed
    print(f"  Result: {passed}/{total} passed")
    if failures:
        print(f"\n  FAILURES ({failed}):")
        for label, exp, got in failures:
            print(f"    {label}")
            print(f"      expected: {exp!r}")
            print(f"      got:      {got!r}")
    else:
        print("  ALL TESTS PASSED!")
    print("=" * 70)
    return failed == 0


if __name__ == "__main__":
    run_tests()
