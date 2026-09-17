"""Explicit, validated runtime configuration without implicit file discovery."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast

from pydantic import BaseModel, ConfigDict, SecretStr, ValidationError

from notes2structure.errors import ConfigurationError

if TYPE_CHECKING:
    from collections.abc import Mapping

_EXPECTED_KEYS = ("N2S_PROVIDER", "N2S_MODEL", "N2S_API_KEY")
_PLACEHOLDERS = frozenset({"change-me", "replace-me", "your-api-key", "sk-..."})


class AppConfig(BaseModel):
    """The small, strict configuration surface for the v0.1 provider."""

    model_config = ConfigDict(extra="forbid", strict=True)

    provider: Literal["openai"]
    model: str
    api_key: SecretStr


def load_configuration(
    env_file: Path | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> AppConfig:
    """Load an explicitly named env file, with process environment taking precedence."""
    file_values = _read_env_file(env_file) if env_file is not None else {}
    process_values = environ if environ is not None else os.environ
    values = {key: process_values.get(key, file_values.get(key)) for key in _EXPECTED_KEYS}
    missing = [key for key, value in values.items() if value is None or not value.strip()]
    if missing:
        message = "Erforderliche Konfiguration fehlt: " + ", ".join(missing)
        raise ConfigurationError(message)

    provider = _required_value(values, "N2S_PROVIDER")
    model = _required_value(values, "N2S_MODEL")
    api_key = _required_value(values, "N2S_API_KEY")
    if api_key.strip().lower() in _PLACEHOLDERS:
        message = "N2S_API_KEY enthält noch einen Platzhalter."
        raise ConfigurationError(message)
    try:
        return AppConfig(
            provider=cast("Literal['openai']", provider),
            model=model,
            api_key=SecretStr(api_key),
        )
    except ValidationError as error:
        message = "Die Provider-Konfiguration ist ungültig. Unterstützt wird N2S_PROVIDER=openai."
        raise ConfigurationError(message) from error


def _read_env_file(path: Path) -> dict[str, str]:
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        message = "Die angegebene Env-Datei konnte nicht gelesen werden."
        raise ConfigurationError(message) from error

    result: dict[str, str] = {}
    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").lstrip()
        key, separator, raw_value = line.partition("=")
        key = key.strip()
        if not separator or not key:
            message = f"Ungültige Zeile {line_number} in der Env-Datei."
            raise ConfigurationError(message)
        if key not in _EXPECTED_KEYS:
            continue
        result[key] = _unquote(raw_value.strip(), line_number)
    return result


def _unquote(value: str, line_number: int) -> str:
    if not value:
        return value
    if value[0] not in {'"', "'"}:
        return value
    if len(value) < len("''") or value[-1] != value[0]:
        message = f"Nicht geschlossenes Anführungszeichen in Zeile {line_number} der Env-Datei."
        raise ConfigurationError(message)
    return value[1:-1]


def _required_value(values: Mapping[str, str | None], key: str) -> str:
    value = values[key]
    if value is None:  # Guarded by the combined missing-value error above.
        message = f"Erforderliche Konfiguration fehlt: {key}"
        raise ConfigurationError(message)
    return value
