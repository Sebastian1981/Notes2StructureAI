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
    KnownType,
    Mode,
    ReinterpretationPayload,
    SegmentStatus,
    Uncertainty,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from notes2structure.providers.base import AnalysisOptions, VisionProvider

DIAGRAM_TYPES = frozenset({DocumentType.MINDMAP, DocumentType.PROCESS, DocumentType.ARCHITECTURE})
DIAGRAM_KNOWN_TYPES = frozenset({KnownType.MINDMAP, KnownType.PROCESS, KnownType.ARCHITECTURE})
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


def reinterpret_document(
    document: DocumentIR,
    requested_type: KnownType,
    provider: VisionProvider,
    *,
    clock: Callable[[], datetime] | None = None,
    run_id_factory: Callable[[], str] | None = None,
) -> DocumentIR:
    """Create a new validated diagram view from an existing analysis without its image."""
    if document.mode is not Mode.FULL:
        message = "Nur eine vollständige Analyse kann als Diagramm neu interpretiert werden."
        raise AnalysisValidationError(message)
    if requested_type not in DIAGRAM_KNOWN_TYPES:
        message = "Die gewünschte Neuinterpretation ist kein Diagrammtyp."
        raise AnalysisValidationError(message)

    payload = provider.reinterpret(document, requested_type)
    _validate_reinterpretation_targets(payload)
    preserved_uncertainties = _preserve_non_graph_uncertainties(document)
    uncertainties = [*preserved_uncertainties, *payload.uncertainties]
    warnings = [
        warning
        for warning in document.warnings
        if not warning.startswith("Gewünschter Dokumenttyp '")
    ]
    warnings.extend(payload.warnings)
    detected = document.classification.detected_type
    type_conflict = False
    if detected is not None and detected.value != requested_type.value:
        type_conflict = True
        if len(warnings) >= MAX_WARNINGS:
            message = "Provider warnings leave no room for the required type-conflict warning."
            raise AnalysisValidationError(message)
        warnings.append(
            f"Gewünschter Dokumenttyp '{requested_type.value}' weicht vom erkannten Typ "
            f"'{detected.value}' ab."
        )

    effective = DocumentType(requested_type.value)
    diagram = _decide_diagram(Mode.FULL, effective, has_nodes=bool(payload.graph.nodes))
    now = (clock or _utc_now)()
    run_id = (run_id_factory or _new_run_id)()
    try:
        merged_payload = AnalysisPayload(
            detected_type=detected,
            classification_reason=document.classification.reason,
            transcript=document.transcript,
            sections=document.sections,
            graph=payload.graph,
            uncertainties=uncertainties,
            warnings=warnings,
        )
        review_required = _calculate_review_required(
            mode=Mode.FULL,
            effective_type=effective,
            type_conflict=type_conflict,
            diagram=diagram,
            payload=merged_payload,
        )
        return DocumentIR(
            schema_version=SCHEMA_VERSION,
            mode=Mode.FULL,
            source=document.source,
            analysis=AnalysisMetadata(
                provider=provider.name,
                model=provider.model,
                prompt_version=provider.reinterpret_prompt_version,
                created_at=_format_timestamp(now),
                run_id=run_id,
            ),
            classification=Classification(
                detected_type=detected,
                requested_type=requested_type,
                effective_type=effective,
                reason=document.classification.reason,
            ),
            transcript=document.transcript,
            sections=document.sections,
            graph=payload.graph,
            uncertainties=uncertainties,
            warnings=warnings,
            review_required=review_required,
            diagram=diagram,
        )
    except ValidationError as error:
        message = "Die Neuinterpretation verletzt den vereinbarten fachlichen Vertrag."
        raise AnalysisValidationError(message) from error


def _validate_reinterpretation_targets(payload: ReinterpretationPayload) -> None:
    graph_ids = {node.id for node in payload.graph.nodes} | {
        edge.id for edge in payload.graph.edges
    }
    invalid_targets = sorted(
        {
            target
            for uncertainty in payload.uncertainties
            for target in uncertainty.target_ids
            if target not in graph_ids
        }
    )
    if invalid_targets:
        message = "Die Neuinterpretation enthält ungültige Unsicherheitsziele."
        raise AnalysisValidationError(message)


def _preserve_non_graph_uncertainties(document: DocumentIR) -> list[Uncertainty]:
    old_graph_ids = {node.id for node in document.graph.nodes} | {
        edge.id for edge in document.graph.edges
    }
    preserved: list[Uncertainty] = []
    for uncertainty in document.uncertainties:
        targets = [target for target in uncertainty.target_ids if target not in old_graph_ids]
        if targets:
            preserved.append(uncertainty.model_copy(update={"target_ids": targets}))
    return preserved


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
