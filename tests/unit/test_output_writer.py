from __future__ import annotations

from pathlib import Path

import pytest

from notes2structure.errors import OutputError
from notes2structure.output_writer import publish_artifacts

RUN_ID = "123e4567e89b42d3a456426614174000"


def test_artifacts_are_published_together_without_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "results"
    artifacts = {"result.json": "{}\n", "transcript.md": "# Text\n"}

    result = publish_artifacts(output, RUN_ID, artifacts)

    assert result == (output / f"run-{RUN_ID}").resolve()
    assert {path.name for path in result.iterdir()} == set(artifacts)
    assert not list(output.glob(".n2s-tmp-*"))
    with pytest.raises(OutputError, match="existiert bereits"):
        publish_artifacts(output, RUN_ID, artifacts)
    assert (result / "result.json").read_text(encoding="utf-8") == "{}\n"


def test_invalid_artifact_name_is_rejected_without_partial_directory(tmp_path: Path) -> None:
    with pytest.raises(OutputError, match="unerlaubte"):
        publish_artifacts(tmp_path, RUN_ID, {"model-supplied.txt": "bad\n"})

    assert not list(tmp_path.iterdir())


def test_non_lf_content_is_rejected_and_temporary_data_is_cleaned(tmp_path: Path) -> None:
    with pytest.raises(OutputError, match="LF-Zeilenenden"):
        publish_artifacts(tmp_path, RUN_ID, {"result.json": "{}\r\n"})

    assert not list(tmp_path.glob(".n2s-tmp-*"))
