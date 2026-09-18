"""Application error categories exposed by the CLI contract."""

from __future__ import annotations


class Notes2StructureError(Exception):
    """Base class for expected, sanitized application failures."""


class InputError(Notes2StructureError):
    """The invocation or input image is invalid."""


class ConfigurationError(Notes2StructureError):
    """Required configuration is missing or unsafe."""


class ProviderError(Notes2StructureError):
    """The configured analysis provider failed."""


class AnalysisValidationError(Notes2StructureError):
    """Provider analysis violates the domain contract."""


class RenderingError(Notes2StructureError):
    """Validated data could not be rendered."""


class OutputError(Notes2StructureError):
    """Rendered artifacts could not be published safely."""
