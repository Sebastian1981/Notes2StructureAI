"""OpenAI Responses API adapter for one bounded vision analysis."""

from __future__ import annotations

import base64
import math
import random
import time
from dataclasses import dataclass
from importlib.resources import files
from typing import TYPE_CHECKING, Protocol, cast

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError
from pydantic import ValidationError

from notes2structure.errors import AnalysisValidationError, InputError, ProviderError
from notes2structure.schemas import AnalysisPayload, Mode

if TYPE_CHECKING:
    from collections.abc import Callable

    from notes2structure.image_reader import NormalizedImage
    from notes2structure.providers.base import AnalysisOptions

PROMPT_VERSION = "analyze-v3"
MAX_ATTEMPTS = 3
ATTEMPT_TIMEOUT_SECONDS = 60.0
TOTAL_TIMEOUT_SECONDS = 200.0
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_IMAGE_DIMENSION = 65_535
MAX_IMAGE_PATCHES = 30_000
PATCH_SIZE = 32
SERVER_ERROR_STATUS = 500
UNAUTHORIZED_STATUS = 401
FORBIDDEN_STATUS = 403


class _ParsedResponse(Protocol):
    output_parsed: object


class _RawResponse(Protocol):
    content: bytes

    def parse(self) -> _ParsedResponse: ...


class _RawResponses(Protocol):
    def parse(self, **kwargs: object) -> _RawResponse: ...


class _Responses(Protocol):
    @property
    def with_raw_response(self) -> _RawResponses: ...


class _OpenAIClient(Protocol):
    @property
    def responses(self) -> _Responses: ...


@dataclass(frozen=True, slots=True)
class RetryHooks:
    sleep: Callable[[float], None] = time.sleep
    monotonic: Callable[[], float] = time.monotonic
    jitter: Callable[[], float] = lambda: random.SystemRandom().uniform(0.0, 0.25)


class OpenAIVisionProvider:
    """Translate normalized image bytes into the strict provider payload."""

    name = "openai"
    prompt_version = PROMPT_VERSION
    is_remote = True

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        client: _OpenAIClient | None = None,
        retry_hooks: RetryHooks | None = None,
    ) -> None:
        self.model = model
        self._client = client or cast(
            "_OpenAIClient",
            OpenAI(api_key=api_key, max_retries=0, timeout=ATTEMPT_TIMEOUT_SECONDS),
        )
        hooks = retry_hooks or RetryHooks()
        self._sleep = hooks.sleep
        self._monotonic = hooks.monotonic
        self._jitter = hooks.jitter
        self._instructions = (
            files("notes2structure.prompts").joinpath("analyze_v3.md").read_text(encoding="utf-8")
        )

    def analyze(self, image: NormalizedImage, options: AnalysisOptions) -> AnalysisPayload:
        _validate_provider_image_limits(image)
        request_input = _build_input(image, options)
        started_at = self._monotonic()

        for attempt in range(1, MAX_ATTEMPTS + 1):
            remaining = TOTAL_TIMEOUT_SECONDS - (self._monotonic() - started_at)
            if remaining <= 0:
                break
            try:
                return self._request_once(request_input, remaining)
            except AnalysisValidationError:
                raise
            except ValidationError as error:
                message = "Der Provider lieferte keine gültige strukturierte Analyse."
                raise AnalysisValidationError(message) from error
            except (APIConnectionError, APITimeoutError, RateLimitError) as error:
                if not self._wait_for_retry(error, attempt, started_at):
                    break
            except APIStatusError as error:
                if error.status_code < SERVER_ERROR_STATUS or not self._wait_for_retry(
                    error, attempt, started_at
                ):
                    message = _status_error_message(error.status_code)
                    raise ProviderError(message) from error
            except Exception as error:  # SDK boundary: never expose remote response details
                message = "Der OpenAI-Provider konnte die Analyse nicht abschließen."
                raise ProviderError(message) from error

        message = "Der OpenAI-Provider ist nach begrenzten Wiederholungen nicht erreichbar."
        raise ProviderError(message)

    def _request_once(
        self, request_input: list[dict[str, object]], remaining: float
    ) -> AnalysisPayload:
        raw_response = self._client.responses.with_raw_response.parse(
            model=self.model,
            instructions=self._instructions,
            input=request_input,
            text_format=AnalysisPayload,
            max_output_tokens=16_000,
            reasoning={"effort": "low"},
            store=False,
            timeout=min(ATTEMPT_TIMEOUT_SECONDS, remaining),
        )
        if len(raw_response.content) > MAX_RESPONSE_BYTES:
            message = "Die Providerantwort überschreitet die Grenze von 2 MiB."
            raise AnalysisValidationError(message)
        payload = raw_response.parse().output_parsed
        if not isinstance(payload, AnalysisPayload):
            message = "Der Provider lieferte keine gültige strukturierte Analyse."
            raise AnalysisValidationError(message)
        return payload

    def _wait_for_retry(self, error: Exception, attempt: int, started_at: float) -> bool:
        if attempt >= MAX_ATTEMPTS:
            return False
        base_delay = float(attempt)
        retry_after = _retry_after_seconds(error)
        delay = (retry_after if retry_after is not None else base_delay) + self._jitter()
        remaining = TOTAL_TIMEOUT_SECONDS - (self._monotonic() - started_at)
        if delay >= remaining:
            return False
        self._sleep(delay)
        return True


def _build_input(image: NormalizedImage, options: AnalysisOptions) -> list[dict[str, object]]:
    encoded = base64.b64encode(image.content).decode("ascii")
    requested_type = options.requested_type.value if options.requested_type is not None else "auto"
    if options.mode is Mode.TRANSCRIBE:
        task = (
            "Mode: transcribe. Set detected_type and classification_reason to null. "
            "Return empty sections, graph nodes and graph edges. Do not create classification "
            "uncertainties."
        )
    else:
        task = (
            f"Mode: full. Requested document type: {requested_type}. Detect the actual type even "
            "when a type was requested. Build only structures directly supported by the image."
        )
    return [
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": task},
                {
                    "type": "input_image",
                    "image_url": f"data:{image.media_type};base64,{encoded}",
                    "detail": "original",
                },
            ],
        }
    ]


def _validate_provider_image_limits(image: NormalizedImage) -> None:
    patches = math.ceil(image.width / PATCH_SIZE) * math.ceil(image.height / PATCH_SIZE)
    if (
        image.width > MAX_IMAGE_DIMENSION
        or image.height > MAX_IMAGE_DIMENSION
        or patches > MAX_IMAGE_PATCHES
    ):
        message = "Das Bild überschreitet die Bildgrenzen des konfigurierten OpenAI-Modells."
        raise InputError(message)


def _retry_after_seconds(error: Exception) -> float | None:
    if not isinstance(error, APIStatusError):
        return None
    raw_value = error.response.headers.get("retry-after")
    if raw_value is None:
        return None
    try:
        value = float(raw_value)
    except ValueError:
        return None
    return value if 0 <= value <= TOTAL_TIMEOUT_SECONDS else None


def _status_error_message(status_code: int) -> str:
    if status_code == UNAUTHORIZED_STATUS:
        return "OpenAI hat den API-Schlüssel nicht akzeptiert."
    if status_code == FORBIDDEN_STATUS:
        return (
            "Das OpenAI-Projekt hat keine Berechtigung für Modell oder API-Zugriff. "
            "Bitte Abrechnung, Projektbudget und Modellzugriff prüfen."
        )
    return "Der OpenAI-Provider hat die Anfrage abgelehnt."
