from __future__ import annotations

import pytest

from notes2structure.cli import main


def test_cli_without_command_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert "Handschriftliche Notizen" in capsys.readouterr().out


def test_cli_reports_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as error:
        main(["--version"])

    assert error.value.code == 0
    assert "notes2structure 0.1.0" in capsys.readouterr().out
