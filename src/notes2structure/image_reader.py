"""Local image validation and privacy-preserving normalization."""

from __future__ import annotations

import hashlib
import io
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from PIL import Image, ImageOps, UnidentifiedImageError

from notes2structure.errors import InputError
from notes2structure.schemas import Source

MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 25_000_000

_EXTENSIONS = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG"}
_MEDIA_TYPES: dict[str, Literal["image/png", "image/jpeg"]] = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
}


@dataclass(frozen=True, slots=True)
class NormalizedImage:
    content: bytes
    media_type: Literal["image/png"]
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class LoadedImage:
    normalized: NormalizedImage
    source: Source


def load_image(path: Path) -> LoadedImage:
    """Read one stable snapshot, validate it, and return a metadata-free RGB PNG."""
    suffix = path.suffix.lower()
    expected_format = _EXTENSIONS.get(suffix)
    if expected_format is None:
        message = "Nur PNG- und JPEG-Dateien werden unterstützt."
        raise InputError(message)
    try:
        if not path.is_file():
            message = "Die Eingabedatei wurde nicht gefunden oder ist keine reguläre Datei."
            raise InputError(message)
        original = _read_limited(path)
    except OSError as error:
        message = "Die Eingabedatei konnte nicht gelesen werden."
        raise InputError(message) from error
    if not original:
        message = "Die Eingabedatei ist leer."
        raise InputError(message)

    normalized, original_format = _decode_and_normalize(original)
    if original_format != expected_format:
        message = "Dateiendung und tatsächliches Bildformat stimmen nicht überein."
        raise InputError(message)

    source = Source(
        filename=path.name,
        sha256=hashlib.sha256(original).hexdigest(),
        media_type=_MEDIA_TYPES[original_format],
        width=normalized.width,
        height=normalized.height,
    )
    return LoadedImage(normalized=normalized, source=source)


def _read_limited(path: Path) -> bytes:
    with path.open("rb") as stream:
        content = stream.read(MAX_FILE_BYTES + 1)
    if len(content) > MAX_FILE_BYTES:
        message = "Die Eingabedatei überschreitet die Grenze von 20 MiB."
        raise InputError(message)
    return content


def _decode_and_normalize(content: bytes) -> tuple[NormalizedImage, str]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                original_format = image.format
                if original_format not in _MEDIA_TYPES:
                    message = "Der Dateiinhalt ist kein unterstütztes PNG- oder JPEG-Bild."
                    raise InputError(message)
                frame_count = getattr(image, "n_frames", 1)
                if frame_count != 1 or getattr(image, "is_animated", False):
                    message = "Animierte oder mehrseitige Bilder werden nicht unterstützt."
                    raise InputError(message)
                if image.width * image.height > MAX_PIXELS:
                    message = "Das Bild überschreitet die Grenze von 25 Millionen Pixeln."
                    raise InputError(message)
                image.load()
                oriented = ImageOps.exif_transpose(image)
                rgb = _flatten_to_rgb(oriented)
                output = io.BytesIO()
                rgb.save(output, format="PNG", optimize=False)
                normalized = NormalizedImage(
                    content=output.getvalue(),
                    media_type="image/png",
                    width=rgb.width,
                    height=rgb.height,
                )
                return normalized, original_format
    except InputError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        message = "Das Bild überschreitet die zulässige Pixelgrenze."
        raise InputError(message) from error
    except (OSError, UnidentifiedImageError, ValueError) as error:
        message = "Die Datei enthält kein gültiges, dekodierbares Bild."
        raise InputError(message) from error


def _flatten_to_rgb(image: Image.Image) -> Image.Image:
    if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        return Image.alpha_composite(background, rgba).convert("RGB")
    return image.convert("RGB")
