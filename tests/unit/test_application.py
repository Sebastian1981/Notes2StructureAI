from __future__ import annotations

from pathlib import Path

import pytest

from notes2structure.application import create_preview, reinterpret_preview, save_preview
from notes2structure.errors import ConfigurationError
from notes2structure.providers.base import AnalysisOptions
from notes2structure.schemas import DocumentType, KnownType, Mode
from tests.support import (
    FakeProvider,
    notes_payload,
    process_reinterpretation_payload,
    write_png,
)


def test_preview_is_not_published_until_user_saves(tmp_path: Path) -> None:
    image = write_png(tmp_path / "note.png")
    output_dir = tmp_path / "output"
    provider = FakeProvider(notes_payload())

    preview = create_preview(
        image,
        AnalysisOptions(Mode.FULL, None),
        provider,
        allow_remote=False,
    )

    assert not output_dir.exists()
    assert provider.calls == 1
    assert "notes.md" in preview.artifacts

    result_dir = save_preview(preview, output_dir)

    assert result_dir.is_dir()
    assert provider.calls == 1
    assert {path.name for path in result_dir.iterdir()} == {
        "result.json",
        "transcript.md",
        "notes.md",
    }


def test_remote_preview_needs_explicit_consent_before_image_read(tmp_path: Path) -> None:
    provider = FakeProvider(notes_payload(), is_remote=True)

    with pytest.raises(ConfigurationError, match="Freigabe"):
        create_preview(
            tmp_path / "missing.png",
            AnalysisOptions(Mode.FULL, None),
            provider,
            allow_remote=False,
        )

    assert provider.calls == 0


def test_preview_can_be_reinterpreted_without_reanalyzing_the_image(tmp_path: Path) -> None:
    image = write_png(tmp_path / "note.png")
    provider = FakeProvider(
        notes_payload(),
        reinterpretation_payload=process_reinterpretation_payload(),
    )
    preview = create_preview(
        image,
        AnalysisOptions(Mode.FULL, None),
        provider,
        allow_remote=False,
    )

    updated = reinterpret_preview(
        preview,
        KnownType.PROCESS,
        provider,
        allow_remote=False,
    )

    assert provider.calls == 1
    assert provider.reinterpret_calls == 1
    assert updated.document.classification.detected_type is DocumentType.NOTES
    assert updated.document.classification.effective_type is DocumentType.PROCESS
    assert updated.document.transcript == preview.document.transcript
    assert "diagram.mmd" in updated.artifacts


def test_remote_reinterpretation_requires_explicit_consent(tmp_path: Path) -> None:
    image = write_png(tmp_path / "note.png")
    provider = FakeProvider(
        notes_payload(),
        reinterpretation_payload=process_reinterpretation_payload(),
    )
    preview = create_preview(
        image,
        AnalysisOptions(Mode.FULL, None),
        provider,
        allow_remote=False,
    )
    provider.is_remote = True

    with pytest.raises(ConfigurationError, match="Übertragungsfreigabe"):
        reinterpret_preview(
            preview,
            KnownType.PROCESS,
            provider,
            allow_remote=False,
        )

    assert provider.reinterpret_calls == 0
