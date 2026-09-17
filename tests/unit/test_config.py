from __future__ import annotations

from pathlib import Path

import pytest

from notes2structure.config import load_configuration
from notes2structure.errors import ConfigurationError


def test_explicit_env_file_is_loaded_without_exposing_secret(tmp_path: Path) -> None:
    env_file = tmp_path / "provider.env"
    env_file.write_text(
        "N2S_PROVIDER=openai\nN2S_MODEL=gpt-5.6-terra\nN2S_API_KEY=secret-value\n",
        encoding="utf-8",
    )

    config = load_configuration(env_file, environ={})

    assert config.provider == "openai"
    assert config.model == "gpt-5.6-terra"
    assert config.api_key.get_secret_value() == "secret-value"
    assert "secret-value" not in repr(config)


def test_process_environment_takes_precedence(tmp_path: Path) -> None:
    env_file = tmp_path / "provider.env"
    env_file.write_text(
        "N2S_PROVIDER=openai\nN2S_MODEL=file-model\nN2S_API_KEY=file-secret\n",
        encoding="utf-8",
    )

    config = load_configuration(
        env_file,
        environ={
            "N2S_PROVIDER": "openai",
            "N2S_MODEL": "environment-model",
            "N2S_API_KEY": "environment-secret",
        },
    )

    assert config.model == "environment-model"
    assert config.api_key.get_secret_value() == "environment-secret"


def test_env_file_is_never_discovered_implicitly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".env").write_text(
        "N2S_PROVIDER=openai\nN2S_MODEL=model\nN2S_API_KEY=secret\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ConfigurationError, match="N2S_PROVIDER"):
        load_configuration(environ={})


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("N2S_PROVIDER=openai\n", "N2S_MODEL"),
        (
            "N2S_PROVIDER=another\nN2S_MODEL=model\nN2S_API_KEY=secret\n",
            "Unterstützt",
        ),
        (
            "N2S_PROVIDER=openai\nN2S_MODEL=model\nN2S_API_KEY=your-api-key\n",
            "Platzhalter",
        ),
        ("not-an-assignment\n", "Zeile 1"),
    ],
)
def test_invalid_configuration_is_rejected(tmp_path: Path, content: str, expected: str) -> None:
    env_file = tmp_path / "provider.env"
    env_file.write_text(content, encoding="utf-8")

    with pytest.raises(ConfigurationError, match=expected):
        load_configuration(env_file, environ={})


def test_error_never_contains_secret(tmp_path: Path) -> None:
    env_file = tmp_path / "provider.env"
    secret = "do-not-print-this-secret"  # noqa: S105 - deliberate leak-safety sentinel
    env_file.write_text(
        f"N2S_PROVIDER=unsupported\nN2S_MODEL=model\nN2S_API_KEY={secret}\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError) as error:
        load_configuration(env_file, environ={})

    assert secret not in str(error.value)
