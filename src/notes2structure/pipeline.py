"""Synchronous orchestration from a local image to validated domain data."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from pydantic import ValidationError

from notes2structure.errors import AnalysisValidationError
from notes2structure.image_reader import load_image
from notes2structure.schemas import (
    SCHEMA_VERSION,
    AnalysisMetadata,
    AnalysisPayload,
    Classification,
    DiagramDecision,
    DiagramStatus,
    DocumentIR,
    DocumentType,
    Mode,
    SegmentStatus,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from notes2structure.providers.base import AnalysisOptions, VisionProvider

DIAGRAM_TYPES = frozenset({DocumentType.MINDMAP, DocumentType.PROCESS, DocumentType.ARCHITECTURE})
MAX_WARNINGS = 100


def analyze_image(
    image_path: Path,
    options: AnalysisOptions,
    provider: VisionProvider,
    *,
    clock: Callable[[], datetime] | None = None,
    run_id_factory: Callable[[], str] | None = None,
) -> DocumentIR:
    """Run one analysis and construct the trusted, fully validated IR."""
    loaded = load_image(image_path)
    payload = provider.analyze(loaded.normalized, options)
    now = (clock or _utc_now)()
    run_id = (run_id_factory or _new_run_id)()

    requested = options.requested_type
    detected = payload.detected_type
    effective = DocumentType(requested.value) if requested is not None else detected
    warnings = list(payload.warnings)
    type_conflict = (
        requested is not None and detected is not None and requested.value != detected.value
    )
    if requested is not None and detected is not None and requested.value != detected.value:
        if len(warnings) >= MAX_WARNINGS:
            message = "Provider warnings leave no room for the required type-conflict warning."
            raise AnalysisValidationError(message)
        warnings.append(
            f"Gewünschter Dokumenttyp '{requested.value}' weicht vom erkannten Typ "
            f"'{detected.value}' ab."
        )

    diagram = _decide_diagram(options.mode, effective, has_nodes=bool(payload.graph.nodes))
    review_required = _calculate_review_required(
        mode=options.mode,
        effective_type=effective,
        type_conflict=type_conflict,
        diagram=diagram,
        payload=payload,
    )
    classification = Classification(
        detected_type=detected,
        requested_type=requested,
        effective_type=effective,
        reason=payload.classification_reason,
    )
    metadata = AnalysisMetadata(
        provider=provider.name,
        model=provider.model,
        prompt_version=provider.prompt_version,
        created_at=_format_timestamp(now),
        run_id=run_id,
    )
    try:
        return DocumentIR(
            schema_version=SCHEMA_VERSION,
            mode=options.mode,
            source=loaded.source,
            analysis=metadata,
            classification=classification,
            transcript=payload.transcript,
            sections=payload.sections,
            graph=payload.graph,
            uncertainties=payload.uncertainties,
            warnings=warnings,
            review_required=review_required,
            diagram=diagram,
        )
    except ValidationError as error:
        message = "Die Provideranalyse verletzt den vereinbarten fachlichen Vertrag."
        raise AnalysisValidationError(message) from error


def _decide_diagram(
    mode: Mode, effective_type: DocumentType | None, *, has_nodes: bool
) -> DiagramDecision:
    if mode is Mode.TRANSCRIBE:
        return DiagramDecision(status=DiagramStatus.NOT_REQUESTED, reason=None)
    if effective_type is None:
        return DiagramDecision(
            status=DiagramStatus.OMITTED,
            reason="Die Dokumentklassifikation fehlt.",
        )
    if effective_type in {DocumentType.NOTES, DocumentType.UNKNOWN}:
        return DiagramDecision(
            status=DiagramStatus.OMITTED,
            reason=f"Für den Dokumenttyp {effective_type.value} ist kein Diagramm vorgesehen.",
        )
    if not has_nodes:
        return DiagramDecision(
            status=DiagramStatus.OMITTED,
            reason="Es konnte keine ausreichend belegte Diagrammstruktur erkannt werden.",
        )
    return DiagramDecision(status=DiagramStatus.GENERATED, reason=None)


def _calculate_review_required(
    *,
    mode: Mode,
    effective_type: DocumentType | None,
    type_conflict: bool,
    diagram: DiagramDecision,
    payload: AnalysisPayload,
) -> bool:
    missing_readable_text = not any(
        segment.status is not SegmentStatus.UNREADABLE for segment in payload.transcript
    )
    return any(
        (
            bool(payload.uncertainties),
            any(segment.status is not SegmentStatus.CLEAR for segment in payload.transcript),
            any(node.uncertain for node in payload.graph.nodes),
            any(edge.uncertain for edge in payload.graph.edges),
            type_conflict,
            mode is Mode.FULL
            and effective_type in DIAGRAM_TYPES
            and diagram.status is DiagramStatus.OMITTED,
            mode is Mode.FULL and effective_type is DocumentType.UNKNOWN,
            missing_readable_text,
        )
    )


def _format_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        message = "The pipeline clock must return a timezone-aware datetime."
        raise AnalysisValidationError(message)
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _new_run_id() -> str:
    return uuid4().hex
