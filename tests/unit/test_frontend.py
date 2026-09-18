from __future__ import annotations

from pathlib import Path

import gradio as gr
import pytest

from notes2structure.application import create_preview
from notes2structure.frontend import (
    ARCHITECTURE,
    AUTO,
    MINDMAP,
    NOTES,
    PROCESS,
    TRANSCRIBE,
    build_frontend,
    preview_to_view,
    selection_to_options,
)
from notes2structure.providers.base import AnalysisOptions
from notes2structure.schemas import KnownType, Mode
from tests.support import FakeProvider, process_payload, write_png


@pytest.mark.parametrize(
    ("selection", "expected"),
    [
        (AUTO, AnalysisOptions(Mode.FULL, None)),
        (TRANSCRIBE, AnalysisOptions(Mode.TRANSCRIBE, None)),
        (NOTES, AnalysisOptions(Mode.FULL, KnownType.NOTES)),
        (MINDMAP, AnalysisOptions(Mode.FULL, KnownType.MINDMAP)),
        (PROCESS, AnalysisOptions(Mode.FULL, KnownType.PROCESS)),
        (ARCHITECTURE, AnalysisOptions(Mode.FULL, KnownType.ARCHITECTURE)),
    ],
)
def test_frontend_selection_maps_to_analysis_options(
    selection: str, expected: AnalysisOptions
) -> None:
    assert selection_to_options(selection) == expected


def test_frontend_view_contains_inline_mermaid_without_saving(tmp_path: Path) -> None:
    image = write_png(tmp_path / "process.png")
    preview = create_preview(
        image,
        AnalysisOptions(Mode.FULL, KnownType.PROCESS),
        FakeProvider(process_payload()),
        allow_remote=False,
    )

    view = preview_to_view(preview)

    assert "noch nicht gespeichert" in view.status
    assert view.diagram.startswith("<svg")
    assert "Start" in view.diagram
    assert "flowchart TD" in view.diagram_source
    assert '"schema_version": "1.0"' in view.result_json


def test_frontend_can_be_built_without_starting_a_server() -> None:
    demo = build_frontend()

    assert isinstance(demo, gr.Blocks)
