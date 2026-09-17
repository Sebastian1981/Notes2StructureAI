"""Canonical JSON rendering for the validated intermediate representation."""

from __future__ import annotations

from notes2structure.schemas import DocumentIR


def render_json(document: DocumentIR) -> str:
    return document.model_dump_json(indent=2) + "\n"
