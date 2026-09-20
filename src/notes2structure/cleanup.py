"""Synchronous orchestration for a faithful visual cleanup."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from pydantic import ValidationError

from notes2structure.errors import AnalysisValidationError
from notes2structure.image_reader import load_image
from notes2structure.schemas import AnalysisMetadata, CleanDocumentIR, SegmentStatus

if TYPE_CHECKING:
    from collections.abc import Callable

    from notes2structure.providers.base import CleanupProvider


def optimize_image(
    image_path: Path,
    provider: CleanupProvider,
    *,
    clock: Callable[[], datetime] | None = None,
    run_id_factory: Callable[[], str] | None = None,
) -> CleanDocumentIR:
    """Analyze one image and construct a trusted clean-note IR."""
    loaded = load_image(image_path)
    payload = provider.optimize(loaded.normalized)
    now = (clock or _utc_now)()
    run_id = (run_id_factory or _new_run_id)()
    review_required = bool(payload.uncertainties) or not any(
        segment.status is SegmentStatus.CLEAR for segment in payload.transcript
    )
    review_required = review_required or any(
        segment.status is not SegmentStatus.CLEAR for segment in payload.transcript
    )
    review_required = review_required or any(
        item.uncertain for item in [*payload.layout.texts, *payload.layout.shapes]
    )
    try:
        return CleanDocumentIR(
            schema_version="clean-note-1.0",
            source=loaded.source,
            analysis=AnalysisMetadata(
                provider=provider.name,
                model=provider.model,
                prompt_version=provider.cleanup_prompt_version,
                created_at=_format_timestamp(now),
                run_id=run_id,
            ),
            transcript=payload.transcript,
            layout=payload.layout,
            uncertainties=payload.uncertainties,
            warnings=payload.warnings,
            review_required=review_required,
        )
    except ValidationError as error:
        message = "Die Optimierung verletzt den vereinbarten fachlichen Vertrag."
        raise AnalysisValidationError(message) from error


def _format_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        message = "The cleanup clock must return a timezone-aware datetime."
        raise AnalysisValidationError(message)
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _new_run_id() -> str:
    return uuid4().hex
