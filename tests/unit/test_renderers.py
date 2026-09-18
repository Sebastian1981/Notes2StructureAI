from __future__ import annotations

from pathlib import Path

from notes2structure.artifacts import render_artifacts
from notes2structure.pipeline import analyze_image
from notes2structure.providers.base import AnalysisOptions
from notes2structure.renderers.mermaid import render_mermaid
from notes2structure.schemas import Mode
from tests.support import (
    FakeProvider,
    notes_payload,
    process_payload,
    uncertain_process_payload,
    write_png,
)


def test_same_document_renders_byte_identically(tmp_path: Path) -> None:
    path = write_png(tmp_path / "note.png")
    document = analyze_image(path, AnalysisOptions(Mode.FULL, None), FakeProvider(notes_payload()))

    assert render_artifacts(document) == render_artifacts(document)


def test_full_notes_create_three_files_without_diagram(tmp_path: Path) -> None:
    path = write_png(tmp_path / "note.png")
    document = analyze_image(path, AnalysisOptions(Mode.FULL, None), FakeProvider(notes_payload()))

    artifacts = render_artifacts(document)

    assert set(artifacts) == {"result.json", "transcript.md", "notes.md"}
    assert all(value.endswith("\n") for value in artifacts.values())


def test_mermaid_escapes_injected_statements_and_uses_fixed_direction(tmp_path: Path) -> None:
    malicious = 'Start"]\nclick n1 "https://example.invalid"\n%%{init: {}}%%'
    path = write_png(tmp_path / "process.png")
    document = analyze_image(
        path,
        AnalysisOptions(Mode.FULL, None),
        FakeProvider(process_payload(first_label=malicious)),
    )

    diagram = render_mermaid(document)

    assert diagram is not None
    assert diagram.startswith("flowchart TD\n")
    assert "\nclick" not in diagram
    assert "%%{" not in diagram
    assert "https://" not in diagram
    assert "#34;" in diagram


def test_markdown_neutralizes_html_and_link_syntax(tmp_path: Path) -> None:
    malicious = "<script>alert(1)</script> [link](https://example.invalid)"
    path = write_png(tmp_path / "note.png")
    document = analyze_image(
        path,
        AnalysisOptions(Mode.FULL, None),
        FakeProvider(notes_payload(text=malicious)),
    )

    artifacts = render_artifacts(document)

    assert "<script>" not in artifacts["transcript.md"]
    assert "[link](" not in artifacts["transcript.md"]
    assert "&lt;script&gt;" in artifacts["transcript.md"]


def test_uncertainty_is_visible_in_notes_and_mermaid(tmp_path: Path) -> None:
    path = write_png(tmp_path / "uncertain.png")
    document = analyze_image(
        path,
        AnalysisOptions(Mode.FULL, None),
        FakeProvider(uncertain_process_payload()),
    )

    artifacts = render_artifacts(document)

    assert document.review_required is True
    assert "**[unsicher]**" in artifacts["notes.md"]
    assert "Zahl 47?" in artifacts["notes.md"]
    assert "#40;?#41;" in artifacts["diagram.mmd"]
    assert "-.->" in artifacts["diagram.mmd"]
