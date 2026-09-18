"""Render the exact artifact set required for a validated document."""

from __future__ import annotations

from notes2structure.errors import RenderingError
from notes2structure.renderers.json import render_json
from notes2structure.renderers.markdown import render_notes, render_transcript
from notes2structure.renderers.mermaid import render_mermaid
from notes2structure.schemas import DocumentIR, Mode


def render_artifacts(document: DocumentIR) -> dict[str, str]:
    try:
        artifacts = {
            "result.json": render_json(document),
            "transcript.md": render_transcript(document),
        }
        if document.mode is Mode.FULL:
            artifacts["notes.md"] = render_notes(document)
        diagram = render_mermaid(document)
        if diagram is not None:
            artifacts["diagram.mmd"] = diagram
        return artifacts
    except (TypeError, ValueError) as error:
        message = "Die validierten Analysedaten konnten nicht gerendert werden."
        raise RenderingError(message) from error
