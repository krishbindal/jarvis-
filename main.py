"""Entry point for JARVIS-X."""
from core.app import JarvisApp


def main() -> None:
    app = JarvisApp()
    app.run()


if __name__ == "__main__":
    main()
