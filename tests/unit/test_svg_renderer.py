from __future__ import annotations

from pathlib import Path

from notes2structure.application import create_preview
from notes2structure.providers.base import AnalysisOptions
from notes2structure.renderers.svg import render_svg_preview
from notes2structure.schemas import Mode
from tests.support import FakeProvider, notes_payload, process_payload, write_png


def test_svg_preview_renders_validated_process_without_active_content(tmp_path: Path) -> None:
    image = write_png(tmp_path / "process.png")
    payload = process_payload(first_label='<script>alert("x")</script>')
    preview = create_preview(
        image,
        AnalysisOptions(Mode.FULL, None),
        FakeProvider(payload),
        allow_remote=False,
    )

    svg = render_svg_preview(preview.document)

    assert svg is not None
    assert svg.startswith("<svg")
    assert "<script>" not in svg
    assert "&lt;script&gt;" in svg
    assert "<line" in svg
    assert "<polygon" in svg


def test_svg_preview_is_absent_for_notes(tmp_path: Path) -> None:
    image = write_png(tmp_path / "notes.png")
    preview = create_preview(
        image,
        AnalysisOptions(Mode.FULL, None),
        FakeProvider(notes_payload()),
        allow_remote=False,
    )

    assert render_svg_preview(preview.document) is None
