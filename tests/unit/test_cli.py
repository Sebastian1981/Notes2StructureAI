from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest

from notes2structure.cli import main
from notes2structure.errors import ProviderError
from notes2structure.image_reader import NormalizedImage
from notes2structure.providers.base import AnalysisOptions
from notes2structure.schemas import AnalysisPayload
from tests.support import (
    FakeProvider,
    notes_payload,
    process_payload,
    transcribe_payload,
    write_png,
)


def test_cli_without_command_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert "Handschriftliche Notizen" in capsys.readouterr().out


def test_cli_reports_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as error:
        main(["--version"])

    assert error.value.code == 0
    assert "notes2structure 0.1.0" in capsys.readouterr().out


def test_cli_without_real_provider_returns_configuration_error(tmp_path: Path) -> None:
    error_stream = StringIO()

    result = main(["analyze", str(tmp_path / "note.png")], stderr=error_stream)

    assert result == 2
    assert "N2S_PROVIDER" in error_stream.getvalue()


def test_full_cli_pipeline_writes_expected_files(tmp_path: Path) -> None:
    image = write_png(tmp_path / "Eingabe ü.png")
    original = image.read_bytes()
    output = tmp_path / "Ausgabe mit Leerzeichen"
    stdout = StringIO()
    stderr = StringIO()

    result = main(
        ["analyze", str(image), "--output-dir", str(output)],
        provider=FakeProvider(notes_payload()),
        stdout=stdout,
        stderr=stderr,
    )

    result_dir = Path(stdout.getvalue().strip())
    assert result == 0
    assert stderr.getvalue() == ""
    assert result_dir.parent == output.resolve()
    assert {path.name for path in result_dir.iterdir()} == {
        "result.json",
        "transcript.md",
        "notes.md",
    }
    assert image.read_bytes() == original


def test_process_cli_pipeline_adds_mermaid(tmp_path: Path) -> None:
    image = write_png(tmp_path / "process.png")
    stdout = StringIO()

    result = main(
        ["analyze", str(image), "--output-dir", str(tmp_path / "output")],
        provider=FakeProvider(process_payload()),
        stdout=stdout,
        stderr=StringIO(),
    )

    assert result == 0
    assert (Path(stdout.getvalue().strip()) / "diagram.mmd").is_file()


def test_transcribe_cli_writes_exactly_two_files(tmp_path: Path) -> None:
    image = write_png(tmp_path / "note.png")
    stdout = StringIO()

    result = main(
        [
            "analyze",
            str(image),
            "--mode",
            "transcribe",
            "--output-dir",
            str(tmp_path / "output"),
        ],
        provider=FakeProvider(transcribe_payload()),
        stdout=stdout,
        stderr=StringIO(),
    )

    assert result == 0
    result_dir = Path(stdout.getvalue().strip())
    assert {path.name for path in result_dir.iterdir()} == {
        "result.json",
        "transcript.md",
    }


def test_transcribe_rejects_type_before_provider_call(tmp_path: Path) -> None:
    provider = FakeProvider(transcribe_payload())
    error_stream = StringIO()

    result = main(
        [
            "analyze",
            str(tmp_path / "missing.png"),
            "--mode",
            "transcribe",
            "--document-type",
            "notes",
        ],
        provider=provider,
        stderr=error_stream,
    )

    assert result == 2
    assert provider.calls == 0
    assert "document-type" in error_stream.getvalue()


def test_invalid_image_never_reaches_provider(tmp_path: Path) -> None:
    provider = FakeProvider(notes_payload())
    error_stream = StringIO()

    result = main(
        ["analyze", str(tmp_path / "missing.png")],
        provider=provider,
        stderr=error_stream,
    )

    assert result == 2
    assert provider.calls == 0
    assert "nicht gefunden" in error_stream.getvalue()


def test_remote_provider_requires_explicit_permission(tmp_path: Path) -> None:
    provider = FakeProvider(notes_payload(), is_remote=True)

    result = main(
        ["analyze", str(tmp_path / "missing.png")],
        provider=provider,
        stderr=StringIO(),
    )

    assert result == 2
    assert provider.calls == 0


class FailingProvider(FakeProvider):
    def analyze(self, image: NormalizedImage, options: AnalysisOptions) -> AnalysisPayload:
        del image, options
        message = "Provider temporarily unavailable."
        raise ProviderError(message)


def test_provider_failure_maps_to_exit_code_three(tmp_path: Path) -> None:
    image = write_png(tmp_path / "note.png")

    result = main(
        ["analyze", str(image)],
        provider=FailingProvider(notes_payload()),
        stderr=StringIO(),
    )

    assert result == 3
