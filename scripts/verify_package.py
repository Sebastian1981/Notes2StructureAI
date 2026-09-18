"""CI smoke test for the installed command and packaged prompt resource."""

from __future__ import annotations

import importlib.resources
import subprocess
import sys

from notes2structure.frontend import build_frontend


def main() -> None:
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "notes2structure.cli", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or "notes2structure 0.1.0" not in result.stdout:
        message = "CLI smoke test failed"
        raise SystemExit(message)
    prompt = importlib.resources.files("notes2structure").joinpath("prompts/analyze_v5.md")
    if not prompt.is_file():
        message = "packaged prompt is missing"
        raise SystemExit(message)
    demo = build_frontend()
    if demo.title != "Notes2StructureAI":
        message = "frontend smoke test failed"
        raise SystemExit(message)


if __name__ == "__main__":
    main()
