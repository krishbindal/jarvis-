"""Measure real headless Qt bootstrap on the CI host.

This is not a microphone, voice, model, or laptop benchmark. No synthetic
performance metrics are generated; every number comes from the current process.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import sys
import time


def main() -> int:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    # Running a script by path puts scripts/ rather than the repository root
    # on sys.path; resolve imports independent of the caller's working directory.
    root = str(Path(__file__).resolve().parents[1])
    if root not in sys.path:
        sys.path.insert(0, root)
    import psutil

    proc = psutil.Process()
    start = time.perf_counter()
    rss_before = proc.memory_info().rss

    from PySide6.QtWidgets import QApplication
    from utils.events import EventBus
    from ui.main_window import JarvisWindow
    from ui.overlay import JarvisOverlay
    modules_ms = (time.perf_counter() - start) * 1000

    qt_start = time.perf_counter()
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    bus = EventBus()
    window = None
    overlay = None
    try:
        window = JarvisWindow(bus)
        overlay = JarvisOverlay(bus)
        window.show()
        overlay.show()
        app.processEvents()
        qt_ms = (time.perf_counter() - qt_start) * 1000
        rss_after = proc.memory_info().rss
        result = {
            "environment": "GitHub Actions headless Qt offscreen (NOT a real Windows desktop)",
            "commit": os.environ.get("GITHUB_SHA"),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "measured": {
                "core_module_import_ms": round(modules_ms, 3),
                "qt_construct_show_process_events_ms": round(qt_ms, 3),
                "rss_before_bytes": int(rss_before),
                "rss_after_bytes": int(rss_after),
            },
            "not_tested": [
                "microphone", "wake-word accuracy", "speakers", "AI API keys",
                "real desktop automation", "user laptop performance",
            ],
        }
        out = Path("artifacts") / "headless_qt_benchmark.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0
    finally:
        # Emit an explicit cleanup trace so a native Qt process exit is
        # distinguishable from a successful benchmark with teardown errors.
        print("[CI-QT] cleanup: started", file=sys.stderr, flush=True)
        if overlay is not None:
            overlay.close()
            print("[CI-QT] cleanup: overlay closed", file=sys.stderr, flush=True)
        if window is not None:
            window.close()
            print("[CI-QT] cleanup: main closed", file=sys.stderr, flush=True)
        app.quit()
        print("[CI-QT] cleanup: done", file=sys.stderr, flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
