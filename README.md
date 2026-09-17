# Notes2StructureAI

Notes2StructureAI ist eine lokale Python-Anwendung, die ein Bild mit handschriftlichen
Notizen oder Skizzen in überprüfbare digitale Artefakte überführt. Die Anwendung bewahrt
die Quellsprache, trennt Transkription von Interpretation und kennzeichnet Unsicherheiten.

Der aktuelle Stand enthält das installierbare Projektgerüst, die CLI-Hilfe und die streng
validierten Datenmodelle. Bildverarbeitung und Vision-Provider folgen in den nächsten
Umsetzungsschritten.

## Lokale Entwicklungsumgebung

Das Projekt verwendet Python 3.12 in einer eigenen `.venv`. Eine andere global installierte
Python-Version wird dadurch nicht ersetzt.

```powershell
uv sync --frozen --group dev
uv run notes2structure --help
```

## Qualitätsprüfungen

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
uv run pre-commit run --all-files
```

Die geplante Bedienung und das vollständige Verhalten stehen in [docs/spec.md](docs/spec.md).
