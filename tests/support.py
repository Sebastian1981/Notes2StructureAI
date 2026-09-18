from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from notes2structure.image_reader import NormalizedImage
from notes2structure.providers.base import AnalysisOptions
from notes2structure.schemas import (
    AnalysisPayload,
    DocumentType,
    Edge,
    Graph,
    Node,
    NodeKind,
    NoteItem,
    NoteSection,
    SegmentStatus,
    TranscriptSegment,
    Uncertainty,
    UncertaintyKind,
)


@dataclass(slots=True)
class FakeProvider:
    payload: AnalysisPayload
    name: str = "fake"
    model: str = "deterministic-test-model"
    prompt_version: str = "analyze-v1"
    is_remote: bool = False
    calls: int = field(default=0, init=False)

    def analyze(self, image: NormalizedImage, options: AnalysisOptions) -> AnalysisPayload:
        del image, options
        self.calls += 1
        return self.payload


def write_png(path: Path, *, size: tuple[int, int] = (4, 3)) -> Path:
    Image.new("RGB", size, "white").save(path, format="PNG")
    return path


def notes_payload(*, text: str = "Prototyp testen") -> AnalysisPayload:
    return AnalysisPayload(
        detected_type=DocumentType.NOTES,
        classification_reason="Eine Textnotiz ohne Diagrammstruktur.",
        transcript=[TranscriptSegment(id="t1", text=text, status=SegmentStatus.CLEAR)],
        sections=[
            NoteSection(
                heading="Notiz",
                items=[NoteItem(text=text, source_ids=["t1"])],
            )
        ],
        graph=Graph(nodes=[], edges=[]),
        uncertainties=[],
        warnings=[],
    )


def transcribe_payload(*, text: str = "Prototyp testen") -> AnalysisPayload:
    return AnalysisPayload(
        detected_type=None,
        classification_reason=None,
        transcript=[TranscriptSegment(id="t1", text=text, status=SegmentStatus.CLEAR)],
        sections=[],
        graph=Graph(nodes=[], edges=[]),
        uncertainties=[],
        warnings=[],
    )


def process_payload(
    *,
    first_label: str = "Start",
    item_text: str = "Start",
    document_type: DocumentType = DocumentType.PROCESS,
) -> AnalysisPayload:
    return AnalysisPayload(
        detected_type=document_type,
        classification_reason="Ein gerichteter Ablauf ist sichtbar.",
        transcript=[TranscriptSegment(id="t1", text=item_text, status=SegmentStatus.CLEAR)],
        sections=[
            NoteSection(
                heading="Ablauf",
                items=[NoteItem(text=item_text, source_ids=["t1"])],
            )
        ],
        graph=Graph(
            nodes=[
                Node(
                    id="n1",
                    label=first_label,
                    kind=NodeKind.STEP,
                    source_ids=["t1"],
                    visual_evidence=None,
                    uncertain=False,
                ),
                Node(
                    id="n2",
                    label="Ende",
                    kind=NodeKind.STEP,
                    source_ids=[],
                    visual_evidence="Sichtbarer zweiter Kasten.",
                    uncertain=False,
                ),
            ],
            edges=[
                Edge(
                    id="e1",
                    source="n1",
                    target="n2",
                    label="weiter",
                    directed=True,
                    source_ids=[],
                    visual_evidence="Sichtbarer Pfeil.",
                    uncertain=False,
                )
            ],
        ),
        uncertainties=[],
        warnings=[],
    )


def unknown_payload() -> AnalysisPayload:
    return AnalysisPayload(
        detected_type=DocumentType.UNKNOWN,
        classification_reason="Keine belastbare Zuordnung möglich.",
        transcript=[],
        sections=[],
        graph=Graph(nodes=[], edges=[]),
        uncertainties=[],
        warnings=["Kein lesbarer Text erkannt."],
    )


def uncertain_process_payload() -> AnalysisPayload:
    payload = process_payload(item_text="Zahl 42?")
    payload.transcript[0] = TranscriptSegment(
        id="t1",
        text="Zahl 42?",
        status=SegmentStatus.UNCERTAIN,
    )
    payload.graph.nodes[0].uncertain = True
    payload.graph.edges[0].uncertain = True
    payload.uncertainties = [
        Uncertainty(
            id="u1",
            kind=UncertaintyKind.TEXT,
            target_ids=["t1", "n1"],
            message="Die Zahl ist schwer lesbar.",
            alternatives=["Zahl 47?"],
        ),
        Uncertainty(
            id="u2",
            kind=UncertaintyKind.RELATION,
            target_ids=["e1"],
            message="Die Pfeilrichtung ist schwach erkennbar.",
            alternatives=[],
        ),
    ]
    return AnalysisPayload.model_validate(payload.model_dump())
