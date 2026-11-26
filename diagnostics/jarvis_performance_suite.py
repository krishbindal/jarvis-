"""Legacy compatibility launcher.

The original file called itself an end-to-end performance suite, but it used
synthetic vectors, referenced removed methods and even marked its failing
checks as completed. Use the real measured, clearly scoped CI benchmark.
"""
from __future__ import annotations


def main() -> int:
    print(
        "The old performance suite has been retired: it is not a valid end-to-end "
        "test or current benchmark.\n"
        "For a measured OFFSCREEN Qt benchmark on Windows CI, run:\n"
        "  python scripts/ci_headless_benchmark.py\n"
        "For device verification, see docs/RELEASE_READINESS.md.\n"
        "No benchmark or hardware verification ran in this command."
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
