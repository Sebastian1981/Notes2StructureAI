from __future__ import annotations

import hashlib
import io
from pathlib import Path

import pytest
from PIL import Image, PngImagePlugin

from notes2structure import image_reader
from notes2structure.errors import InputError
from notes2structure.image_reader import load_image


def test_png_is_hashed_flattened_and_stripped_of_metadata(tmp_path: Path) -> None:
    path = tmp_path / "transparent.png"
    image = Image.new("RGBA", (2, 1), (0, 0, 0, 0))
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("private-note", "must not survive")
    image.save(path, pnginfo=metadata)
    original = path.read_bytes()

    loaded = load_image(path)

    assert loaded.source.sha256 == hashlib.sha256(original).hexdigest()
    assert loaded.source.filename == "transparent.png"
    assert loaded.source.media_type == "image/png"
    assert loaded.normalized.media_type == "image/png"
    with Image.open(io.BytesIO(loaded.normalized.content)) as normalized:
        assert normalized.mode == "RGB"
        assert normalized.getpixel((0, 0)) == (255, 255, 255)
        assert "private-note" not in normalized.info


def test_jpeg_exif_orientation_is_applied(tmp_path: Path) -> None:
    path = tmp_path / "rotated.jpeg"
    exif = Image.Exif()
    exif[274] = 6
    Image.new("RGB", (3, 2), "white").save(path, format="JPEG", exif=exif)

    loaded = load_image(path)

    assert (loaded.source.width, loaded.source.height) == (2, 3)
    assert loaded.source.media_type == "image/jpeg"


@pytest.mark.parametrize("filename", ["missing.png", "missing.JPG"])
def test_missing_file_is_rejected(tmp_path: Path, filename: str) -> None:
    with pytest.raises(InputError, match="nicht gefunden"):
        load_image(tmp_path / filename)


def test_extension_and_real_format_must_match(tmp_path: Path) -> None:
    path = tmp_path / "actually-png.jpg"
    Image.new("RGB", (2, 2), "white").save(path, format="PNG")

    with pytest.raises(InputError, match="stimmen nicht überein"):
        load_image(path)


def test_animated_png_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "animated.png"
    first = Image.new("RGB", (2, 2), "white")
    second = Image.new("RGB", (2, 2), "black")
    first.save(path, save_all=True, append_images=[second], duration=100, loop=0)

    with pytest.raises(InputError, match="Animierte"):
        load_image(path)


def test_invalid_and_empty_files_are_rejected(tmp_path: Path) -> None:
    empty = tmp_path / "empty.png"
    empty.touch()
    invalid = tmp_path / "invalid.png"
    invalid.write_bytes(b"not an image")

    with pytest.raises(InputError, match="leer"):
        load_image(empty)
    with pytest.raises(InputError, match="gültiges"):
        load_image(invalid)


def test_pixel_limit_is_checked_before_provider_use(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "large.png"
    Image.new("RGB", (10, 10), "white").save(path)
    monkeypatch.setattr(image_reader, "MAX_PIXELS", 50)

    with pytest.raises(InputError, match="25 Millionen Pixeln"):
        load_image(path)


def test_file_size_limit_is_enforced(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "large.png"
    path.write_bytes(b"12345")
    monkeypatch.setattr(image_reader, "MAX_FILE_BYTES", 4)

    with pytest.raises(InputError, match="20 MiB"):
        load_image(path)
