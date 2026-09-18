"""Shared application service for CLI and local frontend entry points."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from notes2structure.artifacts import render_artifacts
from notes2structure.config import AppConfig
from notes2structure.errors import ConfigurationError
from notes2structure.output_writer import publish_artifacts
from notes2structure.pipeline import analyze_image, reinterpret_document
from notes2structure.providers.openai import OpenAIVisionProvider

if TYPE_CHECKING:
    from notes2structure.providers.base import AnalysisOptions, VisionProvider
    from notes2structure.schemas import DocumentIR, KnownType


@dataclass(frozen=True, slots=True)
class AnalysisPreview:
    """One validated analysis and its not-yet-published deterministic artifacts."""

    document: DocumentIR
    artifacts: Mapping[str, str]


def build_provider(config: AppConfig) -> VisionProvider:
    """Build the configured concrete provider at the application boundary."""
    return OpenAIVisionProvider(
        api_key=config.api_key.get_secret_value(),
        model=config.model,
    )


def create_preview(
    image_path: Path,
    options: AnalysisOptions,
    provider: VisionProvider,
    *,
    allow_remote: bool,
) -> AnalysisPreview:
    """Analyze and render in memory without publishing an output directory."""
    if provider.is_remote and not allow_remote:
        message = "Für einen externen Provider ist die Freigabe der Bildübertragung erforderlich."
        raise ConfigurationError(message)
    document = analyze_image(image_path, options, provider)
    return AnalysisPreview(document=document, artifacts=render_artifacts(document))


def reinterpret_preview(
    preview: AnalysisPreview,
    requested_type: KnownType,
    provider: VisionProvider,
    *,
    allow_remote: bool,
) -> AnalysisPreview:
    """Create an optional diagram interpretation from validated data, without the image."""
    if provider.is_remote and not allow_remote:
        message = "Für die externe Neuinterpretation ist die Übertragungsfreigabe erforderlich."
        raise ConfigurationError(message)
    document = reinterpret_document(preview.document, requested_type, provider)
    return AnalysisPreview(document=document, artifacts=render_artifacts(document))


def save_preview(preview: AnalysisPreview, output_dir: Path) -> Path:
    """Publish a previously rendered preview without another provider request."""
    return publish_artifacts(
        output_dir,
        preview.document.analysis.run_id,
        dict(preview.artifacts),
    )
