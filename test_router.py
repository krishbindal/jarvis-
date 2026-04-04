from core.command_router import route_command

cases = [
    ("pause music",     "media_control"),
    ("play music",      "media_control"),
    ("stop playback",   "media_control"),
    ("skip this song",  "media_control"),
    ("mute",            "media_control"),
    ("volume up",       "media_control"),
    ("lock computer",   "power_state"),
    ("open chrome",     "open_app"),
    ("open youtube",    "open_url"),
    ("capture screen",  "capture_screen"),
    ("search google python tips", "quick_search"),
]

print("ROUTER VALIDATION")
all_pass = True
for cmd, expected in cases:
    result = route_command(cmd)
    got = result.get("action", "")
    ok = got == expected
    if not ok:
        all_pass = False
    status = "OK" if ok else "FAIL"
    print(f"  [{status}] {cmd!r:35s}  expected={expected}  got={got}")

print()
print("ALL PASS!" if all_pass else "SOME FAILURES")
