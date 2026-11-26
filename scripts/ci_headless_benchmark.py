"""Measure real headless Qt bootstrap on the CI host.

This is not a microphone, voice, model, or laptop benchmark. No synthetic
performance metrics are generated; every number comes from the current process.
"""
from __future__ import annotations

import gc
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
    from PySide6.QtGui import QFontDatabase
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

        # Functional dashboard smoke test: this checks real Qt widgets, not a
        # static mockup or model-invented visual performance.
        for name in ("status_label", "privacy_label", "execution_label", "command_input", "console"):
            assert getattr(window, name, None) is not None, f"Missing dashboard widget: {name}"

        window._prefill_command("system check")
        assert window.command_input.text() == "system check"
        window.command_input.clear()
        window._append_log("<b>literal user text</b>")
        assert "<b>literal user text</b>" in window.console.toPlainText()
        window._on_command_result({
            "status": "error", "success": False, "message": "Simulated denial",
        })
        assert "ATTENTION" in window.status_label.text()
        window._on_command_result({
            "status": "success", "success": True, "message": "Simulated tool result",
        })
        assert "REPORTED SUCCESS" in window.status_label.text()

        # Screenshot is from actual headless Qt rendering, not an illustration.
        preview = Path("artifacts") / "jarvis-dashboard-headless.png"
        preview.parent.mkdir(parents=True, exist_ok=True)
        preview_ok = bool(window.grab().save(str(preview), "PNG"))
        rss_after = proc.memory_info().rss
        result = {
            "environment": "GitHub Actions headless Qt offscreen (NOT a real Windows desktop)",
            "commit": os.environ.get("GITHUB_SHA"),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "headless_font_diagnostics": {
                # A CI rendering can lack user-desktop fonts and show missing glyphs.
                "family_count": len(QFontDatabase.families()),
                "has_segoe_ui": "Segoe UI" in QFontDatabase.families(),
                "has_arial": "Arial" in QFontDatabase.families(),
                "font_samples": QFontDatabase.families()[:12],
            },
            "ui_smoke_checks": {
                "required_dashboard_widgets": 5,
                "literal_text_not_html": True,
                "failure_and_success_states_checked": True,
                "headless_preview_written": preview_ok,
            },
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
        # Qt wrappers must be destroyed while QApplication is still alive.
        # EventBus callbacks otherwise retain SignalBridge/QWidget references
        # past the QApplication lifetime, sometimes causing native teardown errors.
        print("[CI-QT] cleanup: begin", file=sys.stderr, flush=True)
        try:
            if overlay is not None:
                overlay._timer.stop()
                overlay.close()
                overlay.deleteLater()
            if window is not None:
                window._typing_timer.stop()
                window.hud._timer.stop()
                window.hud._stats_timer.stop()
                window.close()
                window.deleteLater()
            with bus._lock:
                bus._handlers.clear()
            app.processEvents()
            overlay = None
            window = None
            gc.collect()
            print("[CI-QT] cleanup: widgets released", file=sys.stderr, flush=True)
        finally:
            app.quit()
            print("[CI-QT] cleanup: QApplication quit", file=sys.stderr, flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
