"""Command-line entry point."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

from notes2structure import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="notes2structure",
        description="Handschriftliche Notizen in geprüfte digitale Artefakte umwandeln.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    analyze = subparsers.add_parser(
        "analyze",
        help="Ein einzelnes PNG- oder JPEG-Bild analysieren (noch nicht implementiert).",
    )
    analyze.add_argument("image", type=Path, help="Pfad zum Eingabebild")
    analyze.add_argument("--output-dir", type=Path, default=Path("output"))
    analyze.add_argument("--mode", choices=("transcribe", "full"), default="full")
    analyze.add_argument(
        "--document-type",
        choices=("auto", "notes", "mindmap", "process", "architecture"),
        default="auto",
    )
    analyze.add_argument(
        "--allow-remote",
        action="store_true",
        help="Externe Übertragung des normalisierten Bildes ausdrücklich erlauben.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    parser.error("Die Analyse-Pipeline wird im nächsten Umsetzungsschritt ergänzt.")
    return 2  # pragma: no cover - argparse exits before this line


if __name__ == "__main__":
    raise SystemExit(main())
