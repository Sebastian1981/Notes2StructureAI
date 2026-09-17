"""Narrow provider boundary used by the synchronous pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from notes2structure.image_reader import NormalizedImage
from notes2structure.schemas import AnalysisPayload, KnownType, Mode


@dataclass(frozen=True, slots=True)
class AnalysisOptions:
    mode: Mode
    requested_type: KnownType | None


class VisionProvider(Protocol):
    name: str
    model: str
    prompt_version: str
    is_remote: bool

    def analyze(self, image: NormalizedImage, options: AnalysisOptions) -> AnalysisPayload: ...
