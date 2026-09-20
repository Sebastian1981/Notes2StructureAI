"""Strict domain models and cross-reference validation for the shared IR."""

from __future__ import annotations

from collections import Counter, deque
from datetime import datetime
from enum import StrEnum
from typing import Annotated, ClassVar, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

SCHEMA_VERSION = "1.0"
NORMALIZED_PAGE_MAX = 1_000
TRANSCRIPT_ID_PATTERN = r"^t[1-9][0-9]*$"
NODE_ID_PATTERN = r"^n[1-9][0-9]*$"
EDGE_ID_PATTERN = r"^e[1-9][0-9]*$"
UNCERTAINTY_ID_PATTERN = r"^u[1-9][0-9]*$"
LAYOUT_TEXT_ID_PATTERN = r"^l[1-9][0-9]*$"
LAYOUT_SHAPE_ID_PATTERN = r"^s[1-9][0-9]*$"

ShortText = Annotated[str, StringConstraints(min_length=1, max_length=500)]
LongText = Annotated[str, StringConstraints(min_length=1, max_length=2_000)]
ContentText = Annotated[str, StringConstraints(min_length=1, max_length=10_000)]
TranscriptId = Annotated[str, StringConstraints(pattern=TRANSCRIPT_ID_PATTERN)]
NodeId = Annotated[str, StringConstraints(pattern=NODE_ID_PATTERN)]
EdgeId = Annotated[str, StringConstraints(pattern=EDGE_ID_PATTERN)]
UncertaintyId = Annotated[str, StringConstraints(pattern=UNCERTAINTY_ID_PATTERN)]
LayoutTextId = Annotated[str, StringConstraints(pattern=LAYOUT_TEXT_ID_PATTERN)]
LayoutShapeId = Annotated[str, StringConstraints(pattern=LAYOUT_SHAPE_ID_PATTERN)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    @field_validator("*", mode="before")
    @classmethod
    def reject_blank_strings(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            msg = "strings must not be blank"
            raise ValueError(msg)
        return value


class Mode(StrEnum):
    TRANSCRIBE = "transcribe"
    FULL = "full"


class KnownType(StrEnum):
    NOTES = "notes"
    MINDMAP = "mindmap"
    PROCESS = "process"
    ARCHITECTURE = "architecture"


class DocumentType(StrEnum):
    NOTES = "notes"
    MINDMAP = "mindmap"
    PROCESS = "process"
    ARCHITECTURE = "architecture"
    UNKNOWN = "unknown"


class SegmentStatus(StrEnum):
    CLEAR = "clear"
    UNCERTAIN = "uncertain"
    UNREADABLE = "unreadable"


class NodeKind(StrEnum):
    TOPIC = "topic"
    STEP = "step"
    DECISION = "decision"
    COMPONENT = "component"
    UNKNOWN = "unknown"


class UncertaintyKind(StrEnum):
    TEXT = "text"
    CLASSIFICATION = "classification"
    STRUCTURE = "structure"
    RELATION = "relation"


class DiagramStatus(StrEnum):
    GENERATED = "generated"
    OMITTED = "omitted"
    NOT_REQUESTED = "not_requested"


class TextRole(StrEnum):
    HEADING = "heading"
    BODY = "body"
    LABEL = "label"
    NOTE = "note"


class TextAlignment(StrEnum):
    LEFT = "left"
    CENTER = "center"


class ShapeKind(StrEnum):
    RECTANGLE = "rectangle"
    ROUNDED_RECTANGLE = "rounded_rectangle"
    ELLIPSE = "ellipse"
    LINE = "line"
    ARROW = "arrow"


class Source(StrictModel):
    filename: ShortText
    sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    media_type: Literal["image/png", "image/jpeg"]
    width: Annotated[int, Field(gt=0)]
    height: Annotated[int, Field(gt=0)]

    @field_validator("filename")
    @classmethod
    def require_base_filename(cls, value: str) -> str:
        if "/" in value or "\\" in value or value in {".", ".."}:
            msg = "filename must be a base name without a path"
            raise ValueError(msg)
        return value


class AnalysisMetadata(StrictModel):
    provider: ShortText
    model: ShortText
    prompt_version: ShortText
    created_at: ShortText
    run_id: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{32}$")]

    @field_validator("created_at")
    @classmethod
    def require_utc_rfc3339(cls, value: str) -> str:
        if not value.endswith("Z"):
            msg = "created_at must be an RFC 3339 UTC timestamp ending in Z"
            raise ValueError(msg)
        try:
            datetime.fromisoformat(value)
        except ValueError as error:
            msg = "created_at must be a valid RFC 3339 timestamp"
            raise ValueError(msg) from error
        return value


class Classification(StrictModel):
    detected_type: DocumentType | None
    requested_type: KnownType | None
    effective_type: DocumentType | None
    reason: LongText | None


class TranscriptSegment(StrictModel):
    id: TranscriptId
    text: ContentText
    status: SegmentStatus

    @model_validator(mode="after")
    def require_unreadable_marker(self) -> Self:
        if self.status is SegmentStatus.UNREADABLE and "[unleserlich]" not in self.text:
            msg = "unreadable transcript segments must contain [unleserlich]"
            raise ValueError(msg)
        return self


class NoteItem(StrictModel):
    text: ContentText
    source_ids: Annotated[list[TranscriptId], Field(min_length=1, max_length=1_000)]


class NoteSection(StrictModel):
    heading: ShortText
    items: Annotated[list[NoteItem], Field(max_length=100)]


class Node(StrictModel):
    id: NodeId
    label: ShortText
    kind: NodeKind
    source_ids: Annotated[list[TranscriptId], Field(max_length=1_000)]
    visual_evidence: LongText | None
    uncertain: bool

    @model_validator(mode="after")
    def require_evidence(self) -> Self:
        if not self.source_ids and self.visual_evidence is None:
            msg = "a graph node needs a transcript reference or visual evidence"
            raise ValueError(msg)
        return self


class Edge(StrictModel):
    id: EdgeId
    source: NodeId
    target: NodeId
    label: ShortText | None
    directed: bool
    source_ids: Annotated[list[TranscriptId], Field(max_length=1_000)]
    visual_evidence: LongText | None
    uncertain: bool

    @model_validator(mode="after")
    def require_evidence(self) -> Self:
        if not self.source_ids and self.visual_evidence is None:
            msg = "a graph edge needs a transcript reference or visual evidence"
            raise ValueError(msg)
        return self


class Graph(StrictModel):
    nodes: Annotated[list[Node], Field(max_length=500)]
    edges: Annotated[list[Edge], Field(max_length=1_000)]


class Uncertainty(StrictModel):
    id: UncertaintyId
    kind: UncertaintyKind
    target_ids: Annotated[list[str], Field(min_length=1, max_length=1_000)]
    message: LongText
    alternatives: Annotated[list[LongText], Field(max_length=10)]


class DiagramDecision(StrictModel):
    status: DiagramStatus
    reason: LongText | None


class AnalysisPayload(StrictModel):
    detected_type: DocumentType | None
    classification_reason: LongText | None
    transcript: Annotated[list[TranscriptSegment], Field(max_length=1_000)]
    sections: Annotated[list[NoteSection], Field(max_length=200)]
    graph: Graph
    uncertainties: Annotated[list[Uncertainty], Field(max_length=1_000)]
    warnings: Annotated[list[LongText], Field(max_length=100)]

    @model_validator(mode="after")
    def validate_references(self) -> Self:
        _validate_content_integrity(self.transcript, self.sections, self.graph, self.uncertainties)
        return self


class ReinterpretationPayload(StrictModel):
    """Graph-only result derived from an already validated analysis."""

    graph: Graph
    uncertainties: Annotated[list[Uncertainty], Field(max_length=1_000)]
    warnings: Annotated[list[LongText], Field(max_length=100)]


NormalizedCoordinate = Annotated[int, Field(ge=0, le=1_000)]
CanvasDimension = Annotated[int, Field(ge=250, le=2_000)]


class LayoutText(StrictModel):
    """One cleaned text block positioned on a normalized page."""

    id: LayoutTextId
    text: ContentText
    role: TextRole
    alignment: TextAlignment
    x: NormalizedCoordinate
    y: NormalizedCoordinate
    width: Annotated[int, Field(gt=0, le=1_000)]
    height: Annotated[int, Field(gt=0, le=1_000)]
    source_ids: Annotated[list[TranscriptId], Field(min_length=1, max_length=1_000)]
    uncertain: bool

    @model_validator(mode="after")
    def require_bounds(self) -> Self:
        if self.x + self.width > NORMALIZED_PAGE_MAX or self.y + self.height > NORMALIZED_PAGE_MAX:
            msg = "layout text bounds must stay within the normalized page"
            raise ValueError(msg)
        return self


class LayoutShape(StrictModel):
    """One cleaned geometric mark using normalized endpoint coordinates."""

    id: LayoutShapeId
    kind: ShapeKind
    x1: NormalizedCoordinate
    y1: NormalizedCoordinate
    x2: NormalizedCoordinate
    y2: NormalizedCoordinate
    source_ids: Annotated[list[TranscriptId], Field(max_length=1_000)]
    visual_evidence: LongText | None
    uncertain: bool

    @model_validator(mode="after")
    def require_geometry_and_evidence(self) -> Self:
        if self.x1 == self.x2 and self.y1 == self.y2:
            msg = "layout shapes must have a visible extent"
            raise ValueError(msg)
        if self.kind in {
            ShapeKind.RECTANGLE,
            ShapeKind.ROUNDED_RECTANGLE,
            ShapeKind.ELLIPSE,
        } and (self.x2 <= self.x1 or self.y2 <= self.y1):
            msg = "area shapes require top-left and bottom-right coordinates"
            raise ValueError(msg)
        if not self.source_ids and self.visual_evidence is None:
            msg = "a layout shape needs a transcript reference or visual evidence"
            raise ValueError(msg)
        return self


class CleanLayout(StrictModel):
    """Provider-described page layout; all coordinates are normalized to 0..1000."""

    canvas_width: CanvasDimension
    canvas_height: CanvasDimension
    texts: Annotated[list[LayoutText], Field(max_length=1_000)]
    shapes: Annotated[list[LayoutShape], Field(max_length=1_000)]


class CleanupPayload(StrictModel):
    """Untrusted provider result for a faithful visual cleanup."""

    transcript: Annotated[list[TranscriptSegment], Field(max_length=1_000)]
    layout: CleanLayout
    uncertainties: Annotated[list[Uncertainty], Field(max_length=1_000)]
    warnings: Annotated[list[LongText], Field(max_length=100)]

    @model_validator(mode="after")
    def validate_cleanup(self) -> Self:
        _validate_cleanup_integrity(
            self.transcript,
            self.layout,
            self.uncertainties,
        )
        return self


class CleanDocumentIR(StrictModel):
    """Trusted intermediate representation for the cleaned visual note."""

    schema_version: Literal["clean-note-1.0"]
    source: Source
    analysis: AnalysisMetadata
    transcript: Annotated[list[TranscriptSegment], Field(max_length=1_000)]
    layout: CleanLayout
    uncertainties: Annotated[list[Uncertainty], Field(max_length=1_000)]
    warnings: Annotated[list[LongText], Field(max_length=100)]
    review_required: bool

    @model_validator(mode="after")
    def validate_document(self) -> Self:
        _validate_cleanup_integrity(
            self.transcript,
            self.layout,
            self.uncertainties,
        )
        expected_review = bool(self.uncertainties) or not any(
            segment.status is SegmentStatus.CLEAR for segment in self.transcript
        )
        expected_review = expected_review or any(
            segment.status is not SegmentStatus.CLEAR for segment in self.transcript
        )
        expected_review = expected_review or any(
            item.uncertain for item in [*self.layout.texts, *self.layout.shapes]
        )
        if self.review_required is not expected_review:
            msg = f"review_required must be {expected_review} for this cleaned document"
            raise ValueError(msg)
        return self


class DocumentIR(StrictModel):
    schema_version: Literal["1.0"]
    mode: Mode
    source: Source
    analysis: AnalysisMetadata
    classification: Classification
    transcript: Annotated[list[TranscriptSegment], Field(max_length=1_000)]
    sections: Annotated[list[NoteSection], Field(max_length=200)]
    graph: Graph
    uncertainties: Annotated[list[Uncertainty], Field(max_length=1_000)]
    warnings: Annotated[list[LongText], Field(max_length=100)]
    review_required: bool
    diagram: DiagramDecision

    diagram_types: ClassVar[frozenset[DocumentType]] = frozenset(
        {DocumentType.MINDMAP, DocumentType.PROCESS, DocumentType.ARCHITECTURE}
    )

    @model_validator(mode="after")
    def validate_document(self) -> Self:
        _validate_content_integrity(self.transcript, self.sections, self.graph, self.uncertainties)
        if self.mode is Mode.TRANSCRIBE:
            self._validate_transcribe_mode()
        else:
            self._validate_full_mode()
        expected_review = self._calculate_review_required()
        if self.review_required is not expected_review:
            msg = f"review_required must be {expected_review} for this document"
            raise ValueError(msg)
        return self

    def _validate_transcribe_mode(self) -> None:
        classification_values = (
            self.classification.detected_type,
            self.classification.requested_type,
            self.classification.effective_type,
            self.classification.reason,
        )
        if any(value is not None for value in classification_values):
            msg = "classification fields must be null in transcribe mode"
            raise ValueError(msg)
        if self.sections or self.graph.nodes or self.graph.edges:
            msg = "sections and graph must be empty in transcribe mode"
            raise ValueError(msg)
        if any(item.kind is UncertaintyKind.CLASSIFICATION for item in self.uncertainties):
            msg = "classification uncertainty is not allowed in transcribe mode"
            raise ValueError(msg)
        if (
            self.diagram.status is not DiagramStatus.NOT_REQUESTED
            or self.diagram.reason is not None
        ):
            msg = "transcribe mode requires diagram status not_requested without a reason"
            raise ValueError(msg)

    def _validate_full_mode(self) -> None:
        classification = self.classification
        if (
            classification.detected_type is None
            or classification.effective_type is None
            or classification.reason is None
        ):
            msg = "full mode requires detected/effective type and classification reason"
            raise ValueError(msg)
        expected_effective = classification.requested_type or classification.detected_type
        if classification.effective_type.value != expected_effective.value:
            msg = "effective_type must equal requested_type when set, otherwise detected_type"
            raise ValueError(msg)
        effective = classification.effective_type
        if effective in {DocumentType.NOTES, DocumentType.UNKNOWN}:
            if self.graph.nodes or self.graph.edges:
                msg = "notes and unknown documents must have an empty graph"
                raise ValueError(msg)
            self._require_omitted_diagram()
            return
        if not self.graph.nodes:
            if self.graph.edges:
                msg = "graph edges require graph nodes"
                raise ValueError(msg)
            self._require_omitted_diagram()
            return
        if self.diagram.status is not DiagramStatus.GENERATED or self.diagram.reason is not None:
            msg = "a usable graph requires diagram status generated without a reason"
            raise ValueError(msg)
        if effective is DocumentType.MINDMAP:
            _validate_mindmap(self.graph)

    def _require_omitted_diagram(self) -> None:
        if self.diagram.status is not DiagramStatus.OMITTED or self.diagram.reason is None:
            msg = "an omitted diagram requires status omitted and a reason"
            raise ValueError(msg)

    def _calculate_review_required(self) -> bool:
        classification = self.classification
        type_conflict = (
            classification.requested_type is not None
            and classification.detected_type is not None
            and classification.requested_type.value != classification.detected_type.value
        )
        expected_diagram_omitted = (
            self.mode is Mode.FULL
            and classification.effective_type in self.diagram_types
            and self.diagram.status is DiagramStatus.OMITTED
        )
        missing_readable_text = not any(
            segment.status is not SegmentStatus.UNREADABLE for segment in self.transcript
        )
        return any(
            (
                bool(self.uncertainties),
                any(segment.status is not SegmentStatus.CLEAR for segment in self.transcript),
                any(node.uncertain for node in self.graph.nodes),
                any(edge.uncertain for edge in self.graph.edges),
                type_conflict,
                expected_diagram_omitted,
                self.mode is Mode.FULL and classification.effective_type is DocumentType.UNKNOWN,
                missing_readable_text,
            )
        )


def _require_unique_ids(values: list[str], collection: str) -> None:
    duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
    if duplicates:
        msg = f"duplicate IDs in {collection}: {', '.join(duplicates)}"
        raise ValueError(msg)


def _validate_content_integrity(
    transcript: list[TranscriptSegment],
    sections: list[NoteSection],
    graph: Graph,
    uncertainties: list[Uncertainty],
) -> None:
    transcript_ids = {segment.id for segment in transcript}
    node_ids = {node.id for node in graph.nodes}
    edge_ids = {edge.id for edge in graph.edges}
    _require_unique_ids([segment.id for segment in transcript], "transcript")
    _require_unique_ids([node.id for node in graph.nodes], "graph nodes")
    _require_unique_ids([edge.id for edge in graph.edges], "graph edges")
    _require_unique_ids([item.id for item in uncertainties], "uncertainties")

    _validate_graph_and_note_references(sections, graph, transcript_ids, node_ids)
    _validate_uncertainties(transcript, graph, uncertainties, transcript_ids | node_ids | edge_ids)


def _validate_graph_and_note_references(
    sections: list[NoteSection],
    graph: Graph,
    transcript_ids: set[str],
    node_ids: set[str],
) -> None:
    for section in sections:
        for item in section.items:
            _require_transcript_references(item.source_ids, transcript_ids)
    for node in graph.nodes:
        _require_transcript_references(node.source_ids, transcript_ids)
    for edge in graph.edges:
        _require_transcript_references(edge.source_ids, transcript_ids)
        if edge.source not in node_ids or edge.target not in node_ids:
            msg = f"edge {edge.id} references a missing graph node"
            raise ValueError(msg)


def _validate_uncertainties(
    transcript: list[TranscriptSegment],
    graph: Graph,
    uncertainties: list[Uncertainty],
    object_ids: set[str],
) -> None:
    valid_targets = object_ids | {"classification"}
    targets_by_id = {target for item in uncertainties for target in item.target_ids}
    for item in uncertainties:
        invalid_targets = sorted(set(item.target_ids) - valid_targets)
        if invalid_targets:
            msg = f"uncertainty {item.id} has invalid targets: {', '.join(invalid_targets)}"
            raise ValueError(msg)
        if item.kind is UncertaintyKind.CLASSIFICATION and "classification" not in item.target_ids:
            msg = "classification uncertainty must target classification"
            raise ValueError(msg)

    required_uncertainty = {
        segment.id for segment in transcript if segment.status is not SegmentStatus.CLEAR
    }
    required_uncertainty.update(node.id for node in graph.nodes if node.uncertain)
    required_uncertainty.update(edge.id for edge in graph.edges if edge.uncertain)
    missing_uncertainty = sorted(required_uncertainty - targets_by_id)
    if missing_uncertainty:
        msg = "uncertain objects need uncertainty entries: " + ", ".join(missing_uncertainty)
        raise ValueError(msg)

    uncertain_transcript_ids = {
        segment.id for segment in transcript if segment.status is not SegmentStatus.CLEAR
    }
    for graph_item in [*graph.nodes, *graph.edges]:
        if (
            uncertain_transcript_ids.intersection(graph_item.source_ids)
            and not graph_item.uncertain
        ):
            msg = f"graph object {graph_item.id} derived from uncertain text must be uncertain"
            raise ValueError(msg)


def _require_transcript_references(
    source_ids: list[TranscriptId], transcript_ids: set[str]
) -> None:
    missing = sorted(set(source_ids) - transcript_ids)
    if missing:
        msg = "missing transcript references: " + ", ".join(missing)
        raise ValueError(msg)


def _validate_mindmap(graph: Graph) -> None:
    if any(not edge.directed for edge in graph.edges):
        msg = "mindmap edges must be directed"
        raise ValueError(msg)
    if len(graph.edges) != len(graph.nodes) - 1:
        msg = "a mindmap must contain exactly one less edge than nodes"
        raise ValueError(msg)
    indegree: Counter[str] = Counter(edge.target for edge in graph.edges)
    roots = [node.id for node in graph.nodes if indegree[node.id] == 0]
    has_invalid_parent_count = any(
        indegree[node.id] != 1 for node in graph.nodes if node.id not in roots
    )
    if len(roots) != 1 or has_invalid_parent_count:
        msg = "a mindmap must have one root and one parent for every other node"
        raise ValueError(msg)
    adjacency: dict[str, list[str]] = {node.id: [] for node in graph.nodes}
    for edge in graph.edges:
        adjacency[edge.source].append(edge.target)
    visited: set[str] = set()
    pending = deque(roots)
    while pending:
        node_id = pending.popleft()
        if node_id in visited:
            msg = "a mindmap must not contain cycles"
            raise ValueError(msg)
        visited.add(node_id)
        pending.extend(adjacency[node_id])
    if len(visited) != len(graph.nodes):
        msg = "a mindmap must be connected"
        raise ValueError(msg)


def _validate_cleanup_integrity(
    transcript: list[TranscriptSegment],
    layout: CleanLayout,
    uncertainties: list[Uncertainty],
) -> None:
    transcript_ids = {segment.id for segment in transcript}
    text_ids = {item.id for item in layout.texts}
    shape_ids = {item.id for item in layout.shapes}
    _require_unique_ids([segment.id for segment in transcript], "transcript")
    _require_unique_ids([item.id for item in layout.texts], "layout texts")
    _require_unique_ids([item.id for item in layout.shapes], "layout shapes")
    _require_unique_ids([item.id for item in uncertainties], "uncertainties")

    for item in [*layout.texts, *layout.shapes]:
        _require_transcript_references(item.source_ids, transcript_ids)

    valid_targets = transcript_ids | text_ids | shape_ids
    targets_by_id = {target for item in uncertainties for target in item.target_ids}
    for uncertainty in uncertainties:
        invalid_targets = sorted(set(uncertainty.target_ids) - valid_targets)
        if invalid_targets:
            msg = f"uncertainty {uncertainty.id} has invalid targets: {', '.join(invalid_targets)}"
            raise ValueError(msg)
        if uncertainty.kind is UncertaintyKind.CLASSIFICATION:
            msg = "classification uncertainty is not used for visual cleanup"
            raise ValueError(msg)

    required_uncertainty = {
        segment.id for segment in transcript if segment.status is not SegmentStatus.CLEAR
    }
    required_uncertainty.update(item.id for item in layout.texts if item.uncertain)
    required_uncertainty.update(item.id for item in layout.shapes if item.uncertain)
    missing_uncertainty = sorted(required_uncertainty - targets_by_id)
    if missing_uncertainty:
        msg = "uncertain cleanup objects need uncertainty entries: " + ", ".join(
            missing_uncertainty
        )
        raise ValueError(msg)

    uncertain_transcript_ids = {
        segment.id for segment in transcript if segment.status is not SegmentStatus.CLEAR
    }
    for item in [*layout.texts, *layout.shapes]:
        if uncertain_transcript_ids.intersection(item.source_ids) and not item.uncertain:
            msg = f"layout object {item.id} derived from uncertain text must be uncertain"
            raise ValueError(msg)
