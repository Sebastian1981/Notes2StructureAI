"""Command-line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from collections.abc import Sequence

from notes2structure import __version__
from notes2structure.artifacts import render_artifacts
from notes2structure.config import AppConfig, load_configuration
from notes2structure.errors import (
    AnalysisValidationError,
    ConfigurationError,
    InputError,
    Notes2StructureError,
    OutputError,
    ProviderError,
    RenderingError,
)
from notes2structure.output_writer import publish_artifacts
from notes2structure.pipeline import analyze_image
from notes2structure.providers.base import AnalysisOptions, VisionProvider
from notes2structure.providers.openai import OpenAIVisionProvider
from notes2structure.schemas import KnownType, Mode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="notes2structure",
        description="Handschriftliche Notizen in geprüfte digitale Artefakte umwandeln.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")
    analyze = subparsers.add_parser(
        "analyze",
        help="Ein einzelnes PNG- oder JPEG-Bild analysieren.",
    )
    analyze.add_argument("image", type=Path, help="Pfad zum Eingabebild")
    analyze.add_argument("--output-dir", type=Path, default=Path("output"))
    analyze.add_argument(
        "--env-file",
        type=Path,
        help="Konfiguration ausdrücklich aus dieser Env-Datei laden.",
    )
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


def main(
    argv: Sequence[str] | None = None,
    *,
    provider: VisionProvider | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output_stream = stdout or sys.stdout
    error_stream = stderr or sys.stderr
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help(file=output_stream)
        return 0
    try:
        mode = Mode(args.mode)
        requested_type = _parse_requested_type(args.document_type)
        if mode is Mode.TRANSCRIBE and requested_type is not None:
            message = "Im Modus transcribe muss --document-type auf auto stehen."
            raise InputError(message)
        if provider is None:
            provider = _build_provider(load_configuration(args.env_file))
        if provider.is_remote and not args.allow_remote:
            message = "Für einen externen Provider ist --allow-remote erforderlich."
            raise ConfigurationError(message)
        options = AnalysisOptions(mode=mode, requested_type=requested_type)
        document = analyze_image(args.image, options, provider)
        artifacts = render_artifacts(document)
        result_dir = publish_artifacts(args.output_dir, document.analysis.run_id, artifacts)
        if document.review_required:
            error_stream.write("Warnung: Das Ergebnis erfordert eine menschliche Prüfung.\n")
        output_stream.write(f"{result_dir}\n")
        return 0
    except Notes2StructureError as error:
        error_stream.write(f"Fehler: {error}\n")
        return _exit_code(error)
    except Exception:  # noqa: BLE001 - outer CLI boundary sanitizes unknown failures
        error_stream.write("Fehler: Unerwarteter interner Fehler.\n")
        return 1


def _parse_requested_type(value: str) -> KnownType | None:
    return None if value == "auto" else KnownType(value)


def _build_provider(config: AppConfig) -> VisionProvider:
    return OpenAIVisionProvider(
        api_key=config.api_key.get_secret_value(),
        model=config.model,
    )


def _exit_code(error: Notes2StructureError) -> int:
    if isinstance(error, (InputError, ConfigurationError)):
        return 2
    if isinstance(error, ProviderError):
        return 3
    if isinstance(error, AnalysisValidationError):
        return 4
    if isinstance(error, (RenderingError, OutputError)):
        return 5
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
