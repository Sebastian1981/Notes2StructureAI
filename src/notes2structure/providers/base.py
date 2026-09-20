"""Narrow provider boundary used by the synchronous pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from notes2structure.image_reader import NormalizedImage
from notes2structure.schemas import (
    AnalysisPayload,
    CleanupPayload,
    DocumentIR,
    KnownType,
    Mode,
    ReinterpretationPayload,
)


@dataclass(frozen=True, slots=True)
class AnalysisOptions:
    mode: Mode
    requested_type: KnownType | None


class VisionProvider(Protocol):
    name: str
    model: str
    prompt_version: str
    reinterpret_prompt_version: str
    is_remote: bool

    def analyze(self, image: NormalizedImage, options: AnalysisOptions) -> AnalysisPayload: ...

    def reinterpret(
        self, document: DocumentIR, requested_type: KnownType
    ) -> ReinterpretationPayload: ...


class CleanupProvider(Protocol):
    """Provider capability for one faithful image-to-layout cleanup."""

    name: str
    model: str
    cleanup_prompt_version: str
    is_remote: bool

    def optimize(self, image: NormalizedImage) -> CleanupPayload: ...
