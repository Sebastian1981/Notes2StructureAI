from __future__ import annotations

from pathlib import Path

import gradio as gr

from notes2structure.application import create_preview
from notes2structure.frontend import build_frontend, preview_to_view
from notes2structure.providers.base import AnalysisOptions
from notes2structure.schemas import Mode
from tests.support import FakeProvider, process_payload, write_png


def test_frontend_view_contains_inline_mermaid_without_saving(tmp_path: Path) -> None:
    image = write_png(tmp_path / "process.png")
    preview = create_preview(
        image,
        AnalysisOptions(Mode.FULL, None),
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
