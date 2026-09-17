"""Atomic publication of a fixed set of UTF-8 text artifacts."""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from notes2structure.errors import OutputError

ALLOWED_ARTIFACTS = frozenset({"result.json", "transcript.md", "notes.md", "diagram.mmd"})


def publish_artifacts(
    output_dir: Path,
    run_id: str,
    artifacts: dict[str, str],
) -> Path:
    """Write a complete artifact set and publish it with one directory rename."""
    if not artifacts or not set(artifacts).issubset(ALLOWED_ARTIFACTS):
        message = "Die Artefaktliste enthält unerlaubte oder keine Dateinamen."
        raise OutputError(message)
    final_dir = output_dir / f"run-{run_id}"
    temporary_dir = output_dir / f".n2s-tmp-{uuid4().hex}"
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        if not output_dir.is_dir():
            message = "Das Ausgabeverzeichnis ist kein Verzeichnis."
            raise OutputError(message)
        if final_dir.exists():
            message = "Das vorgesehene Ergebnisverzeichnis existiert bereits."
            raise OutputError(message)
        temporary_dir.mkdir(exist_ok=False)
        for filename in sorted(artifacts):
            content = artifacts[filename]
            if not content.endswith("\n") or "\r" in content:
                message = "Textartefakte müssen LF-Zeilenenden und einen Abschlussumbruch haben."
                raise OutputError(message)
            with (temporary_dir / filename).open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
        temporary_dir.rename(final_dir)
        return final_dir.resolve()
    except OutputError:
        _remove_own_temporary_directory(temporary_dir, output_dir)
        raise
    except OSError as error:
        _remove_own_temporary_directory(temporary_dir, output_dir)
        message = "Die Ergebnisdateien konnten nicht sicher veröffentlicht werden."
        raise OutputError(message) from error


def _remove_own_temporary_directory(temporary_dir: Path, output_dir: Path) -> None:
    if (
        temporary_dir.parent == output_dir
        and temporary_dir.name.startswith(".n2s-tmp-")
        and temporary_dir.exists()
    ):
        shutil.rmtree(temporary_dir, ignore_errors=True)
