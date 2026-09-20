from __future__ import annotations

from pathlib import Path

import gradio as gr

from notes2structure.application import create_cleanup_preview
from notes2structure.frontend import build_frontend, preview_to_view
from tests.support import FakeProvider, cleanup_payload, notes_payload, write_png


def test_frontend_view_contains_cleaned_note_without_saving(tmp_path: Path) -> None:
    image = write_png(tmp_path / "note.png")
    preview = create_cleanup_preview(
        image,
        FakeProvider(notes_payload(), cleanup_payload=cleanup_payload()),
        allow_remote=False,
    )

    view = preview_to_view(preview)

    assert "noch nicht gespeichert" in view.status
    assert view.optimized_note.startswith("<svg")
    assert "Projekt planen" in view.optimized_note
    assert '"schema_version": "clean-note-1.0"' in view.result_json


def test_frontend_can_be_built_without_starting_a_server() -> None:
    demo = build_frontend()

    assert isinstance(demo, gr.Blocks)
