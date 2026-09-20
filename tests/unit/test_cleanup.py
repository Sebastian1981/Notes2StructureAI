from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from notes2structure.application import create_cleanup_preview, save_cleanup_preview
from notes2structure.cleanup import optimize_image
from notes2structure.errors import ConfigurationError
from notes2structure.renderers.clean_note import render_clean_svg
from tests.support import FakeProvider, cleanup_payload, notes_payload, write_png


def test_cleanup_creates_faithful_layout_and_safe_svg(tmp_path: Path) -> None:
    image = write_png(tmp_path / "notiz.png")
    provider = FakeProvider(notes_payload(), cleanup_payload=cleanup_payload())

    document = optimize_image(
        image,
        provider,
        clock=lambda: datetime(2026, 9, 20, 10, 0, tzinfo=UTC),
        run_id_factory=lambda: "123e4567e89b42d3a456426614174000",
    )
    svg = render_clean_svg(document)

    assert provider.optimize_calls == 1
    assert document.schema_version == "clean-note-1.0"
    assert "Projekt planen" in svg
    assert "Prototyp testen" in svg
    assert "marker-end" in svg
    assert "<script" not in svg


def test_cleanup_svg_escapes_provider_text(tmp_path: Path) -> None:
    image = write_png(tmp_path / "notiz.png")
    payload = cleanup_payload()
    payload.transcript[0].text = '<script>alert("x")</script>'
    payload.layout.texts[0].text = '<script>alert("x")</script>'
    provider = FakeProvider(notes_payload(), cleanup_payload=payload)

    document = optimize_image(image, provider)
    svg = render_clean_svg(document)

    assert "<script" not in svg
    assert "&lt;script&gt;" in svg


def test_cleanup_preview_is_only_published_after_save(tmp_path: Path) -> None:
    image = write_png(tmp_path / "notiz.png")
    output_dir = tmp_path / "output"
    provider = FakeProvider(notes_payload(), cleanup_payload=cleanup_payload())

    preview = create_cleanup_preview(image, provider, allow_remote=False)

    assert not output_dir.exists()
    assert set(preview.artifacts) == {
        "optimized-note.svg",
        "result.json",
        "transcript.md",
    }

    result_dir = save_cleanup_preview(preview, output_dir)

    assert {path.name for path in result_dir.iterdir()} == set(preview.artifacts)
    assert provider.optimize_calls == 1


def test_remote_cleanup_needs_explicit_consent_before_image_read(tmp_path: Path) -> None:
    provider = FakeProvider(
        notes_payload(),
        cleanup_payload=cleanup_payload(),
        is_remote=True,
    )

    with pytest.raises(ConfigurationError, match="Freigabe"):
        create_cleanup_preview(
            tmp_path / "missing.png",
            provider,
            allow_remote=False,
        )

    assert provider.optimize_calls == 0
