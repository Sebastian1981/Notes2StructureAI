from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import httpx2
import pytest
from openai import (
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    PermissionDeniedError,
    RateLimitError,
)

from notes2structure.errors import AnalysisValidationError, InputError, ProviderError
from notes2structure.image_reader import NormalizedImage
from notes2structure.pipeline import analyze_image
from notes2structure.providers.base import AnalysisOptions
from notes2structure.providers.openai import MAX_RESPONSE_BYTES, OpenAIVisionProvider, RetryHooks
from notes2structure.schemas import AnalysisPayload, KnownType, Mode, ReinterpretationPayload
from tests.support import (
    FakeProvider,
    notes_payload,
    process_reinterpretation_payload,
    transcribe_payload,
    write_png,
)

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(slots=True)
class FakeParsedResponse:
    output_parsed: object


@dataclass(slots=True)
class FakeRawResponse:
    payload: object
    content: bytes = b"{}"
    parse_calls: int = field(default=0, init=False)

    def parse(self) -> FakeParsedResponse:
        self.parse_calls += 1
        return FakeParsedResponse(self.payload)


@dataclass(slots=True)
class FakeRawResponses:
    outcomes: list[FakeRawResponse | Exception]
    calls: list[dict[str, object]] = field(default_factory=list[dict[str, object]])

    def parse(self, **kwargs: object) -> FakeRawResponse:
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@dataclass(slots=True)
class FakeResponses:
    with_raw_response: FakeRawResponses


@dataclass(slots=True)
class FakeClient:
    responses: FakeResponses


def make_provider(
    outcomes: list[FakeRawResponse | Exception],
    *,
    sleep: Callable[[float], None] = lambda _delay: None,
) -> tuple[OpenAIVisionProvider, FakeRawResponses]:
    raw_responses = FakeRawResponses(outcomes)
    client = FakeClient(FakeResponses(raw_responses))
    provider = OpenAIVisionProvider(
        api_key="test-secret",
        model="gpt-5.6-terra",
        client=client,
        retry_hooks=RetryHooks(sleep=sleep, monotonic=lambda: 0.0, jitter=lambda: 0.0),
    )
    return provider, raw_responses


def normalized_image(*, width: int = 2, height: int = 2) -> NormalizedImage:
    return NormalizedImage(
        content=b"normalized-png", media_type="image/png", width=width, height=height
    )


def test_request_uses_structured_output_original_detail_and_no_storage() -> None:
    payload = notes_payload()
    raw = FakeRawResponse(payload)
    provider, requests = make_provider([raw])

    result = provider.analyze(
        normalized_image(), AnalysisOptions(mode=Mode.FULL, requested_type=None)
    )

    assert result == payload
    assert raw.parse_calls == 1
    request = requests.calls[0]
    assert request["store"] is False
    assert request["text_format"] is AnalysisPayload
    assert request["timeout"] == 60.0
    assert provider.prompt_version == "analyze-v5"
    instructions = request["instructions"]
    assert isinstance(instructions, str)
    assert "`kind` is `classification`, `target_ids` must contain the exact literal" in instructions
    assert "use the requested type when it is not `auto`" in instructions
    assert "single most plausible reading directly into the" in instructions
    assert "state that the word was reconstructed" in instructions
    assert "Use `[unleserlich]` and status `unreadable` only" in instructions
    assert "uncertain numbers, identifiers, personal names" in instructions
    assert "effective analysis type is `notes` or `unknown`" in instructions
    assert "exactly one fewer edge than nodes" in instructions
    assert (
        "Every `source_ids`, graph endpoint, and uncertainty target must reference" in instructions
    )
    request_input = request["input"]
    assert isinstance(request_input, list)
    content = request_input[0]["content"]  # type: ignore[index]
    image_part = content[1]  # type: ignore[index]
    assert image_part["detail"] == "original"  # type: ignore[index]
    assert image_part["image_url"].startswith("data:image/png;base64,")  # type: ignore[index, union-attr]


def test_transcribe_mode_is_explicit_in_request() -> None:
    provider, requests = make_provider([FakeRawResponse(transcribe_payload())])

    provider.analyze(normalized_image(), AnalysisOptions(mode=Mode.TRANSCRIBE, requested_type=None))

    request_input = requests.calls[0]["input"]
    assert isinstance(request_input, list)
    content = request_input[0]["content"]  # type: ignore[index]
    assert "Mode: transcribe" in content[0]["text"]  # type: ignore[index, operator]


def test_reinterpretation_uses_only_validated_json_without_an_image(tmp_path: Path) -> None:
    document = analyze_image(
        write_png(tmp_path / "note.png"),
        AnalysisOptions(mode=Mode.FULL, requested_type=None),
        FakeProvider(notes_payload()),
    )
    payload = process_reinterpretation_payload()
    provider, requests = make_provider([FakeRawResponse(payload)])

    result = provider.reinterpret(document, KnownType.PROCESS)

    assert result == payload
    request = requests.calls[0]
    assert request["text_format"] is ReinterpretationPayload
    assert request["store"] is False
    instructions = request["instructions"]
    assert isinstance(instructions, str)
    assert "You do not have access to" in instructions
    assert "the original image in this request" in instructions
    request_input = request["input"]
    assert isinstance(request_input, list)
    content = request_input[0]["content"]  # type: ignore[index]
    assert len(content) == 1  # type: ignore[arg-type]
    assert content[0]["type"] == "input_text"  # type: ignore[index]
    assert 'requested_type":"process' in content[0]["text"]  # type: ignore[index, operator]


def test_timeout_is_retried_at_most_three_times() -> None:
    request = httpx2.Request("POST", "https://api.openai.com/v1/responses")
    sleeps: list[float] = []
    provider, raw_responses = make_provider(
        [APITimeoutError(request), APITimeoutError(request), FakeRawResponse(notes_payload())],
        sleep=sleeps.append,
    )

    result = provider.analyze(
        normalized_image(), AnalysisOptions(mode=Mode.FULL, requested_type=None)
    )

    assert result == notes_payload()
    assert len(raw_responses.calls) == 3
    assert sleeps == [1.0, 2.0]


@pytest.mark.parametrize(
    ("status", "error_type"), [(429, RateLimitError), (503, InternalServerError)]
)
def test_transient_http_errors_are_retried(
    status: int,
    error_type: type[RateLimitError | InternalServerError],
) -> None:
    request = httpx2.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx2.Response(status, request=request)
    provider, raw_responses = make_provider(
        [error_type("temporary", response=response, body=None), FakeRawResponse(notes_payload())]
    )

    result = provider.analyze(
        normalized_image(), AnalysisOptions(mode=Mode.FULL, requested_type=None)
    )

    assert result == notes_payload()
    assert len(raw_responses.calls) == 2


def test_authentication_error_is_not_retried_or_exposed() -> None:
    request = httpx2.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx2.Response(401, request=request)
    provider, raw_responses = make_provider(
        [AuthenticationError("secret remote detail", response=response, body=None)]
    )

    with pytest.raises(ProviderError) as error:
        provider.analyze(normalized_image(), AnalysisOptions(mode=Mode.FULL, requested_type=None))

    assert len(raw_responses.calls) == 1
    assert "secret remote detail" not in str(error.value)


def test_permission_error_explains_safe_next_steps() -> None:
    request = httpx2.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx2.Response(403, request=request)
    provider, raw_responses = make_provider(
        [PermissionDeniedError("private response", response=response, body=None)]
    )

    with pytest.raises(ProviderError, match="Abrechnung, Projektbudget und Modellzugriff") as error:
        provider.analyze(normalized_image(), AnalysisOptions(mode=Mode.FULL, requested_type=None))

    assert len(raw_responses.calls) == 1
    assert "private response" not in str(error.value)


def test_oversized_response_is_rejected_before_parsing() -> None:
    raw = FakeRawResponse(notes_payload(), content=b"x" * (MAX_RESPONSE_BYTES + 1))
    provider, _requests = make_provider([raw])

    with pytest.raises(AnalysisValidationError, match="2 MiB"):
        provider.analyze(normalized_image(), AnalysisOptions(mode=Mode.FULL, requested_type=None))

    assert raw.parse_calls == 0


def test_missing_structured_payload_is_rejected() -> None:
    provider, _requests = make_provider([FakeRawResponse(None)])

    with pytest.raises(AnalysisValidationError, match="strukturierte Analyse"):
        provider.analyze(normalized_image(), AnalysisOptions(mode=Mode.FULL, requested_type=None))


def test_provider_image_limit_is_checked_before_request() -> None:
    provider, raw_responses = make_provider([FakeRawResponse(notes_payload())])

    with pytest.raises(InputError, match="Bildgrenzen"):
        provider.analyze(
            normalized_image(width=65_536, height=1),
            AnalysisOptions(mode=Mode.FULL, requested_type=None),
        )

    assert raw_responses.calls == []
