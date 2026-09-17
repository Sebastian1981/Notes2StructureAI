from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from notes2structure.errors import AnalysisValidationError
from notes2structure.pipeline import analyze_image
from notes2structure.providers.base import AnalysisOptions
from notes2structure.schemas import DocumentIR, DocumentType, KnownType, Mode
from tests.support import (
    FakeProvider,
    notes_payload,
    process_payload,
    transcribe_payload,
    unknown_payload,
    write_png,
)

FIXED_TIME = datetime(2026, 9, 17, 10, 0, tzinfo=UTC)
FIXED_RUN_ID = "123e4567e89b42d3a456426614174000"


def analyze(path: Path, provider: FakeProvider, options: AnalysisOptions) -> DocumentIR:
    return analyze_image(
        path,
        options,
        provider,
        clock=lambda: FIXED_TIME,
        run_id_factory=lambda: FIXED_RUN_ID,
    )


def test_full_notes_document_is_completed_from_trusted_metadata(tmp_path: Path) -> None:
    path = write_png(tmp_path / "note.png")
    provider = FakeProvider(notes_payload())

    document = analyze(path, provider, AnalysisOptions(Mode.FULL, None))

    assert document.classification.effective_type is DocumentType.NOTES
    assert document.diagram.status.value == "omitted"
    assert document.review_required is False
    assert document.analysis.run_id == FIXED_RUN_ID
    assert provider.calls == 1


def test_transcribe_mode_has_no_classification_or_diagram(tmp_path: Path) -> None:
    path = write_png(tmp_path / "note.png")
    provider = FakeProvider(transcribe_payload())

    document = analyze(path, provider, AnalysisOptions(Mode.TRANSCRIBE, None))

    assert document.classification.detected_type is None
    assert document.sections == []
    assert document.diagram.status.value == "not_requested"


def test_requested_type_conflict_is_visible_and_requires_review(tmp_path: Path) -> None:
    path = write_png(tmp_path / "note.png")
    provider = FakeProvider(process_payload())

    document = analyze(
        path,
        provider,
        AnalysisOptions(Mode.FULL, KnownType.ARCHITECTURE),
    )

    assert document.classification.detected_type is DocumentType.PROCESS
    assert document.classification.effective_type is DocumentType.ARCHITECTURE
    assert document.review_required is True
    assert "weicht" in document.warnings[-1]


def test_payload_for_wrong_mode_is_rejected_as_analysis_error(tmp_path: Path) -> None:
    path = write_png(tmp_path / "note.png")
    provider = FakeProvider(notes_payload())

    with pytest.raises(AnalysisValidationError, match="fachlichen Vertrag"):
        analyze(path, provider, AnalysisOptions(Mode.TRANSCRIBE, None))


@pytest.mark.parametrize(
    "document_type",
    [DocumentType.MINDMAP, DocumentType.PROCESS, DocumentType.ARCHITECTURE],
)
def test_all_diagram_document_types_generate_a_graph(
    tmp_path: Path, document_type: DocumentType
) -> None:
    path = write_png(tmp_path / f"{document_type.value}.png")
    provider = FakeProvider(process_payload(document_type=document_type))

    document = analyze(path, provider, AnalysisOptions(Mode.FULL, None))

    assert document.classification.effective_type is document_type
    assert document.diagram.status.value == "generated"


def test_unknown_empty_document_is_successful_but_requires_review(tmp_path: Path) -> None:
    path = write_png(tmp_path / "empty.png")

    document = analyze(
        path,
        FakeProvider(unknown_payload()),
        AnalysisOptions(Mode.FULL, None),
    )

    assert document.classification.effective_type is DocumentType.UNKNOWN
    assert document.diagram.status.value == "omitted"
    assert document.review_required is True
