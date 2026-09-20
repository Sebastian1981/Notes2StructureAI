# Notes2StructureAI

Notes2StructureAI ist eine lokale Python-Anwendung, die eine handschriftliche Seite visuell
aufräumt. Erkennbarer Inhalt, Gruppierung und relative Anordnung sowie sichtbare Kästen, Linien
und Pfeile bleiben erhalten, werden aber als saubere digitale SVG-Seite neu gezeichnet.
Unsicherheiten bleiben sichtbar, statt durch erfundene Inhalte verdeckt zu werden.

Der aktuelle Stand enthält sichere lokale Bildprüfung und Normalisierung, die streng validierte
Pipeline, validierte Layoutdaten, sichere SVG-Ausgabe, einen OpenAI-Vision-Adapter sowie ein
schlankes lokales Browser-Frontend. Die bestehende CLI unterstützt weiterhin die bisherigen
Analyseartefakte. Die normale Testsuite verwendet ausschließlich einen
Fake-Provider und benötigt weder Netzwerk noch API-Schlüssel.

## Lokale Entwicklungsumgebung

Das Projekt verwendet Python 3.12 in einer eigenen `.venv`. Eine andere global installierte
Python-Version wird dadurch nicht ersetzt.

```powershell
uv sync --frozen --group dev
uv run notes2structure --help
```

## Ein eigenes Bild analysieren

Die `.env` wird absichtlich nicht automatisch gesucht. Gib sie ausdrücklich an und bestätige
mit `--allow-remote`, dass das normalisierte Bild an OpenAI übertragen werden darf:

```powershell
uv run notes2structure analyze "C:\Pfad\zu\notiz.jpg" `
  --env-file .env `
  --allow-remote `
  --output-dir output
```

Bei Erfolg steht in der letzten Ausgabezeile der neu angelegte Ergebnisordner. Darin liegen
mindestens `result.json`, `transcript.md` und im Modus `full` zusätzlich `notes.md`; bei einer
belastbaren Diagrammstruktur kommt `diagram.mmd` hinzu. Die Quelldatei bleibt unverändert.

Ohne `--allow-remote` wird kein Bild übertragen. Die nötigen Variablen und Platzhalter stehen
in `.env.example`. Details zur bewussten Anbieterwahl und zu Datenschutzgrenzen dokumentiert
[docs/provider-openai.md](docs/provider-openai.md).

## Lokales Frontend starten

Lege die Provider-Konfiguration wie für die CLI in `.env` ab und starte anschließend:

```powershell
uv run notes2structure-ui
```

Die Anwendung öffnet `http://127.0.0.1:7860` im Browser. Dort kannst du ein PNG/JPEG per
Dateiauswahl oder Drag-and-drop ablegen oder einen OneNote-Screenshot direkt aus der
Zwischenablage einfügen. **Notiz optimieren** überträgt das normalisierte Bild einmal und erzeugt
eine aufgeräumte Vorschau. Eine Auswahl zwischen Notiz, Mindmap oder Prozess ist nicht nötig.

Vor jeder externen Analyse muss die Checkbox zur Bildübertragung aktiviert werden. Die
Oberfläche selbst ist nur lokal erreichbar; Gradio-Telemetrie und öffentliche Freigabelinks sind
deaktiviert. Die optimierte SVG-Seite, der erkannte Inhalt und die validierten Layoutdaten erscheinen
zunächst nur als Vorschau. Erst **Ergebnis speichern** erzeugt einen neuen `run-...`-Ordner mit
`optimized-note.svg`, `transcript.md` und `result.json`. **Verwerfen** oder ein Bildwechsel entfernt
die Vorschau ohne Veröffentlichung. Bereits erfolgte Provideraufrufe können unabhängig vom
Speichern Kosten verursacht haben.

## Qualitätsprüfungen

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
uv run pre-commit run --all-files
```

Die geplante Bedienung und das vollständige Verhalten stehen in [docs/spec.md](docs/spec.md).
Die priorisierten Arbeitspakete werden im [Produkt-Backlog](docs/backlog.md) gepflegt.
