from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from notes2structure.schemas import DocumentIR

FIXTURE = Path(__file__).parents[1] / "fixtures" / "minimal_document.json"


def load_fixture() -> dict[str, object]:
    return cast("dict[str, object]", json.loads(FIXTURE.read_text(encoding="utf-8")))


def test_architecture_example_is_valid() -> None:
    document = DocumentIR.model_validate_json(FIXTURE.read_text(encoding="utf-8"))

    assert document.schema_version == "1.0"
    assert document.transcript[0].text == "Prototyp testen"


def test_extra_fields_are_rejected() -> None:
    data = load_fixture()
    data["unexpected"] = True

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        DocumentIR.model_validate(data, strict=False)


def test_duplicate_transcript_ids_are_rejected() -> None:
    data = load_fixture()
    transcript = cast("list[dict[str, object]]", data["transcript"])
    transcript.append({"id": "t1", "text": "Noch ein Text", "status": "clear"})

    with pytest.raises(ValidationError, match="duplicate IDs in transcript"):
        DocumentIR.model_validate(data, strict=False)


def test_missing_note_reference_is_rejected() -> None:
    data = load_fixture()
    sections = cast("list[dict[str, object]]", data["sections"])
    items = cast("list[dict[str, object]]", sections[0]["items"])
    items[0]["source_ids"] = ["t99"]

    with pytest.raises(ValidationError, match="missing transcript references: t99"):
        DocumentIR.model_validate(data, strict=False)


def test_transcribe_mode_rejects_classification() -> None:
    data = load_fixture()
    data["mode"] = "transcribe"

    with pytest.raises(ValidationError, match="classification fields must be null"):
        DocumentIR.model_validate(data, strict=False)


def test_review_flag_is_derived_from_content() -> None:
    data = load_fixture()
    data["review_required"] = True

    with pytest.raises(ValidationError, match="review_required must be False"):
        DocumentIR.model_validate(data, strict=False)
