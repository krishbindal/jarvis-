"""Reliable command-line entry point for JARVIS-X."""
from __future__ import annotations

import argparse
import socket
import sys


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="JARVIS-X desktop assistant")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--doctor", action="store_true", help="Check setup without starting the UI")
    group.add_argument("--install-autostart", action="store_true", help="Opt in to Windows login startup")
    group.add_argument("--remove-autostart", action="store_true", help="Remove the Windows login startup script")
    parser.add_argument("--wait-for-clap", action="store_true", help="Wait for double clap instead of opening the UI")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    # Keep diagnostics and autostart maintenance independent of GUI/audio imports.
    if args.doctor:
        try:
            from utils.diagnostics import run_diagnostics
            return 0 if run_diagnostics() else 1
        except (ValueError, TypeError) as exc:
            print(f"Invalid configuration: {exc}", file=sys.stderr)
            print("Check environment variables and your .env file.", file=sys.stderr)
            return 1

    if args.install_autostart or args.remove_autostart:
        from utils.startup import enable_autostart, disable_autostart
        success = enable_autostart() if args.install_autostart else disable_autostart()
        print("Windows login startup updated." if success else "Unable to change startup settings; check the logs.")
        return 0 if success else 1

    try:
        from core.app import JarvisApp
    except (ImportError, OSError) as exc:
        print(f"Cannot start Jarvis: {exc}", file=sys.stderr)
        print("Install dependencies: python -m pip install -r requirements.txt", file=sys.stderr)
        print("Then run: python main.py --doctor", file=sys.stderr)
        return 1

    # Retain the lock for the lifetime of the process; never alter login startup implicitly.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as lock:
        try:
            lock.bind(("127.0.0.1", 9999))
        except OSError as exc:
            print("Jarvis is already running, or port 9999 is in use.", file=sys.stderr)
            print(f"Details: {exc}", file=sys.stderr)
            return 1
        try:
            app = JarvisApp(auto_start=not args.wait_for_clap)
            app.run()
            return 0
        except KeyboardInterrupt:
            return 0
        except Exception as exc:
            print(f"Jarvis failed: {exc}", file=sys.stderr)
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
