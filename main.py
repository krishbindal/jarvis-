"""Entry point for JARVIS-X."""
from core.app import JarvisApp
from utils.startup import enable_autostart


def main() -> None:
    # Ensure background start on future boots
    enable_autostart()
    app = JarvisApp()
    app.run()


if __name__ == "__main__":
    main()
