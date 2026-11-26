"""Compatibility entry point for evidence-only Jarvis diagnostics.

Legacy master checks claimed ONLINE from the presence of API keys, PASS when
only one voice dependency existed, and FULLY OPERATIONAL despite warnings.
This command now prints real, scoped observations with truthful limitations.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

if __package__ in (None, ""):
    # Support both python -m diagnostics.final_report and direct script invocation.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from diagnostics.evidence import collect_evidence, render_markdown, write_report


class JarvisMasterCheck:
    """Read-only, conservative runtime inventory (not an end-to-end test)."""

    def __init__(self) -> None:
        self.last_report = None

    def run_all(self, *, probe_ollama: bool = False, output_dir: str | Path = "artifacts/readiness") -> dict:
        self.last_report = collect_evidence(probe_ollama=probe_ollama)
        json_path, md_path = write_report(self.last_report, Path(output_dir))
        print(render_markdown(self.last_report))
        print(f"Saved observed diagnostics: {json_path} and {md_path}")
        return self.last_report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read-only Jarvis system inventory")
    parser.add_argument("--probe-ollama", action="store_true")
    parser.add_argument("--output-dir", default="artifacts/readiness")
    args = parser.parse_args()
    JarvisMasterCheck().run_all(probe_ollama=args.probe_ollama, output_dir=args.output_dir)
