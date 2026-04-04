from core.command_router import route_command

tests = [
    ("hi",                     "chat"),
    ("hello",                  "chat"),
    ("how are you",            "chat"),
    ("can you open youtube",   "open_url"),
    ("now go to downloads",    "open_folder"),
    ("can you pause music",    "media_control"),
    ("open youtube on chrome", "open_url"),
    ("will you open chrome",   "open_app"),
    ("lock computer",          "power_state"),
    ("skip this song",         "media_control"),
]

print("QUICK SMOKE TEST — JARVIS ROUTER")
passed = 0
for cmd, exp in tests:
    r = route_command(cmd)
    got = r.get("action")
    ok = got == exp
    if ok:
        passed += 1
    status = "OK" if ok else "FAIL"
    print(f"  [{status}] {cmd!r:40s} -> {got!r:20s}  (expected {exp!r})")

print()
print(f"Result: {passed}/{len(tests)} passed")
