"""Generate current, scoped readiness evidence without invented statuses."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

if __package__ in (None, ""):
    # Support both python -m diagnostics.final_report and direct script invocation.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from diagnostics.evidence import collect_evidence, render_markdown, write_report


def generate_report(output_dir: str | Path = "artifacts/readiness", *, probe_ollama: bool = False) -> dict:
    """Write an evidence JSON and Markdown report for the actual current host."""
    report = collect_evidence(probe_ollama=probe_ollama)
    json_path, md_path = write_report(report, Path(output_dir))
    print(render_markdown(report))
    print(f"Readiness evidence saved to: {json_path} and {md_path}")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Jarvis non-invasive readiness evidence")
    parser.add_argument("--output-dir", default="artifacts/readiness")
    parser.add_argument("--probe-ollama", action="store_true", help="Probe local Ollama HTTP only")
    args = parser.parse_args()
    generate_report(args.output_dir, probe_ollama=args.probe_ollama)
