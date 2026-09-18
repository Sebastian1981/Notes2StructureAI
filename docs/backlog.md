# Notes2StructureAI — Produkt-Backlog

Stand: 18. September 2026

Dieses Backlog zerlegt die Anforderungen aus [spec.md](spec.md) und
[architecture.md](architecture.md) in kleine, überprüfbare Arbeitspakete. Die Spezifikation
bleibt für das Produktverhalten maßgeblich. Eine Story ist erst erledigt, wenn die
Definition of Done aus [AGENTS.md](../AGENTS.md) erfüllt ist.

## Status und Arbeitsweise

| Status | Bedeutung |
| --- | --- |
| `Erledigt` | Lokal implementiert, dokumentiert und mit den vorgesehenen Prüfungen verifiziert |
| `Prüfung offen` | Implementiert, aber eine externe oder manuelle Prüfung steht noch aus |
| `Als Nächstes` | Nächstes vorgesehenes Arbeitspaket |
| `Geplant` | Fachlich beschrieben, aber noch nicht begonnen |
| `Blockiert` | Benötigt zuerst eine Entscheidung oder ein anderes Arbeitspaket |

Für jede Story wird ein eigener kleiner Branch empfohlen. Implementierung und passende
Tests gehören in denselben Arbeitsgang. Vor Abschluss werden mindestens Ruff,
Formatprüfung, Pyright und pytest ausgeführt. Nicht ausgeführte Prüfungen werden offen
genannt.

## Epic 1 — Projektfundament

Ziel: Das Projekt kann reproduzierbar installiert, gestartet, geprüft und als Python-Paket
gebaut werden. Die gemeinsame Datenstruktur ist streng validiert.

| ID | User Story | Abnahmekriterien | Status |
| --- | --- | --- | --- |
| US-001 | Als Entwickler möchte ich eine isolierte Python-3.12-Umgebung, damit das Projekt keine globale Python-Installation verändert. | `.venv`, `.python-version`, `pyproject.toml` und `uv.lock` sind vorhanden; `uv sync --frozen --group dev` funktioniert. | `Erledigt` |
| US-002 | Als Nutzer möchte ich eine installierbare CLI-Hilfe, damit Bedienung und Datenschutzfreigabe erkennbar sind. | Der Befehl `notes2structure --help` funktioniert; `analyze` und `--allow-remote` werden angezeigt. | `Erledigt` |
| US-003 | Als Anwendung möchte ich ein strenges Datenmodell, damit ungültige Providerdaten nicht weiterverarbeitet werden. | Pydantic-v2-Modelle bilden die IR aus der Architektur ab; Zusatzfelder und falsche Typen werden abgelehnt. | `Erledigt` |
| US-004 | Als Anwendung möchte ich fachliche Querverweise und Invarianten prüfen, damit scheinbar gültiges, aber widersprüchliches JSON abgelehnt wird. | IDs, Referenzen, Modi, Unsicherheiten, Diagrammstatus, Prüfstatus und Mindmap-Baumstruktur werden validiert und getestet. | `Erledigt` |
| US-005 | Als Team möchte ich automatische Qualitätsprüfungen, damit Fehler früh auffallen. | Ruff, Pyright, pytest, pre-commit und Paketbau laufen lokal erfolgreich; CI ist für Windows und Linux konfiguriert. | `Prüfung offen` — erster GitHub-Lauf fehlt |

## Epic 2 — Sichere Bildannahme und Normalisierung

Ziel: Ein einzelnes PNG- oder JPEG-Bild wird vollständig lokal geprüft und in ein
metadatenfreies Providerformat überführt. Vor erfolgreicher Prüfung findet kein
Provideraufruf statt.

| ID | User Story | Abnahmekriterien | Status |
| --- | --- | --- | --- |
| US-006 | Als Nutzer möchte ich ein PNG- oder JPEG-Bild sicher einlesen, damit ungültige Eingaben vor der Analyse verständlich abgelehnt werden. | Pfad, Dateigröße, tatsächliches Format, Endung, Dekodierbarkeit, Animation und Pixelgrenze werden gemäß IN-01/IN-02 geprüft; Tests decken Erfolgs- und Fehlerfälle ab. | `Erledigt` |
| US-007 | Als Nutzer möchte ich korrekt ausgerichtete Bilder analysieren, damit EXIF-Orientierung die Erkennung nicht verfälscht. | EXIF-Orientierung wird angewendet und die normalisierten Abmessungen werden festgehalten. | `Erledigt` |
| US-008 | Als Nutzer möchte ich keine Bildmetadaten übertragen, damit unnötige private Informationen lokal bleiben. | Transparenz wird auf Weiß aufgelöst; das Bild wird als RGB ohne EXIF/GPS neu kodiert; Tests prüfen die Ausgabe. | `Erledigt` |
| US-009 | Als Anwendung möchte ich die Quelle nachvollziehbar beschreiben, ohne private Pfade zu speichern. | SHA-256 des ursprünglichen Snapshots, Basisdateiname, Original-Medientyp und normalisierte Abmessungen werden erzeugt; kein absoluter Pfad wird übernommen. | `Erledigt` |

Zugeordnete Abnahme: AC-05, Teile von AC-01 und AC-06.

## Epic 3 — Lokale Pipeline mit Fake-Provider

Ziel: Der vollständige fachliche Ablauf kann offline, reproduzierbar und ohne API-Schlüssel
getestet werden.

| ID | User Story | Abnahmekriterien | Status |
| --- | --- | --- | --- |
| US-010 | Als Entwickler möchte ich einen schmalen Provider-Vertrag und einen Test-Fake, damit die Pipeline ohne Netzwerk geprüft werden kann. | `VisionProvider`, `NormalizedImage` und `AnalysisOptions` sind typisiert; der Fake liegt ausschließlich in den Tests. | `Erledigt` |
| US-011 | Als Nutzer möchte ich den Modus `transcribe` verwenden, damit ausschließlich Transkription und Unsicherheiten entstehen. | Nur Transkriptionsdaten werden akzeptiert; Typvorgaben werden abgelehnt; es entstehen genau `result.json` und `transcript.md`. | `Erledigt` |
| US-012 | Als Nutzer möchte ich den Modus `full` verwenden, damit Transkription, Struktur, Klassifikation und mögliche Graphdaten gemeinsam entstehen. | Erkanntes, gewünschtes und effektives Format bleiben getrennt; Typkonflikte und fehlende Diagramme werden sichtbar. | `Erledigt` |
| US-013 | Als Nutzer möchte ich Unsicherheit ausdrücklich sehen, damit Modellvermutungen nicht als sichere Fakten erscheinen. | Unleserliche Texte, Alternativen, unsichere Graphobjekte, Warnungen und `review_required` entsprechen der Spezifikation. | `Erledigt` |
| US-014 | Als Nutzer möchte ich verständliche Fehler und Exitcodes, damit Eingabe-, Provider-, Validierungs- und Ausgabefehler unterscheidbar sind. | Definierte Fehlerklassen werden an der CLI-Grenze auf Exitcodes 1–5 abgebildet; sensible Inhalte erscheinen nicht in Meldungen oder Logs. | `Erledigt` |

Zugeordnete Abnahme: AC-01 bis AC-04, AC-07 und AC-11.

## Epic 4 — Deterministische Artefakte und sichere Ausgabe

Ziel: Aus derselben validierten IR entstehen byteidentische Dateien, die atomar in einem
neuen Laufverzeichnis veröffentlicht werden.

| ID | User Story | Abnahmekriterien | Status |
| --- | --- | --- | --- |
| US-015 | Als Nutzer möchte ich ein nachvollziehbares Transkript und strukturierte Notizen, damit Originalinhalt, Interpretation und Unsicherheit getrennt prüfbar sind. | Markdown-Renderer sind reine Funktionen; Referenzen, Warnungen und Prüfstatus sind sichtbar; HTML aus Modelltext wird nicht aktiv übernommen. | `Erledigt` |
| US-016 | Als Nutzer möchte ich für geeignete Dokumente ein sicheres Mermaid-Diagramm, damit Beziehungen visuell darstellbar sind. | Flowchart-Richtung, Knotenformen und Kanten stammen aus festen Templates; Labels werden zentral escaped; unsichere Elemente sind markiert. | `Erledigt` |
| US-017 | Als Nutzer möchte ich Ergebnisse ohne Überschreiben speichern, damit frühere Läufe erhalten bleiben. | Alle Inhalte werden zuerst in ein temporäres Geschwisterverzeichnis geschrieben und anschließend als neues `run-<uuid>` veröffentlicht; Fehler hinterlassen kein fertiges Teilresultat. | `Erledigt` |
| US-018 | Als Nutzer möchte ich den vollständigen CLI-Ablauf offline testen, damit Modi, Dateien und Exitcodes vor der Provideranbindung feststehen. | End-to-End-Tests verwenden synthetische Bilder und Fake-Provider; Pfade mit Leerzeichen und Unicode funktionieren. | `Erledigt` |

Zugeordnete Abnahme: AC-01 bis AC-04, AC-09 bis AC-11.

## Epic 5 — Echter Vision-Provider

Ziel: Ein bewusst gewählter Vision-Dienst wird hinter dem bestehenden Vertrag angebunden.
Ohne ausdrückliche Freigabe werden keine Bilddaten übertragen.

| ID | User Story | Abnahmekriterien | Status |
| --- | --- | --- | --- |
| US-019 | Als Projektverantwortlicher möchte ich den Vision-Anbieter bewusst auswählen, damit Kosten, Handschriftunterstützung und Datenschutz dokumentiert sind. | Anbieter, Modell, SDK-Version, Datenübertragung, Timeoutverhalten und bekannte Grenzen werden als Entscheidung dokumentiert. | `Erledigt` |
| US-020 | Als Nutzer möchte ich Provider und Secret sicher konfigurieren, damit Zugangsdaten weder in Argumenten noch in Logs oder Ergebnissen erscheinen. | Validierte Umgebungsvariablen und optionales `--env-file` funktionieren; gesetzte Umgebung hat Vorrang; Platzhalter stehen in `.env.example`. | `Erledigt` |
| US-021 | Als Nutzer möchte ich jeder externen Übertragung ausdrücklich zustimmen, damit kein Bild versehentlich das Gerät verlässt. | Ohne `--allow-remote` gibt es null Requests und Exitcode 2; nur normalisiertes Bild und notwendiger Prompt werden übertragen. | `Erledigt` |
| US-022 | Als Nutzer möchte ich begrenzte, verständliche Providerfehlerbehandlung, damit vorübergehende Fehler nicht zu unkontrollierten Kosten führen. | Höchstens drei Versuche, festgelegte Zeitgrenzen und nur erlaubte Retry-Fälle; SDK-Retries sind nicht zusätzlich aktiv. | `Erledigt` |
| US-023 | Als Anwendung möchte ich Providerantworten lokal validieren, damit ungültiges oder eingeschleustes Modellformat nicht als Ergebnis veröffentlicht wird. | Antwortgröße ist begrenzt; keine automatische Reparatur; SDK-Daten werden in `AnalysisPayload` übersetzt und anschließend streng validiert. | `Erledigt` |
| US-029 | Als Nutzer möchte ich bei teilweise lesbaren gewöhnlichen Wörtern die plausibelste Lesart sehen, damit Transkript und Diagramm praktisch nutzbar bleiben. | Die Lesart steht im unsicheren Segment; Rekonstruktion und Alternativen bleiben sichtbar; Zahlen, Kennungen und Eigennamen werden nicht kontextuell geraten. | `Erledigt` |

Zugeordnete Abnahme: AC-06 bis AC-08.

## Epic 6 — MVP-Abnahme und Releasevorbereitung

Ziel: Automatisierte Softwarequalität und manuell geprüfte Erkennungsqualität werden getrennt
nachgewiesen.

| ID | User Story | Abnahmekriterien | Status |
| --- | --- | --- | --- |
| US-024 | Als Team möchte ich Mermaid-Ausgaben adversarial prüfen, damit Modelltext keine aktiven Anweisungen einschleusen kann. | Repräsentative und bösartige Labels werden mit einer fest versionierten Mermaid-Parser-Version geprüft. | `Geplant` |
| US-025 | Als Team möchte ich Installation und Paketinhalt in CI prüfen, damit CLI und Prompt-Ressourcen auch außerhalb des Arbeitsverzeichnisses funktionieren. | Windows- und Linux-Jobs installieren das gebaute Paket und prüfen Entry-Point sowie Prompt-Datei. | `Geplant` |
| US-026 | Als Projektverantwortlicher möchte ich einen schlanken Sicherheitscheck, damit offensichtliche Dependency- und Secret-Probleme vor einem öffentlichen Release erkannt werden. | Festgelegter Dependency-Audit und Secret-Scan laufen; relevante Befunde sind behoben oder begründet dokumentiert. | `Geplant` |
| US-027 | Als Nutzer möchte ich reale Beispiele manuell vergleichen, damit Softwaretests nicht mit Erkennungsqualität verwechselt werden. | Mindestens ein freigegebenes Bild je Kerntyp plus ein schwieriges Beispiel werden mit Original, Modell- und Prompt-Version dokumentiert geprüft. | `Blockiert` — benötigt echten Provider und freigegebene Bilder |
| US-028 | Als Nutzer möchte ich eine verständliche Einrichtungs- und Bedienungsanleitung, damit der MVP ohne Entwicklungswissen gestartet werden kann. | README beschreibt Installation, Konfiguration, Datenschutzfreigabe, Beispielaufrufe, Ausgaben und bekannte Grenzen. | `Geplant` |

Zugeordnete Abnahme: AC-10, AC-12 und AC-13.

## Epic 7 — Lokales Showcase-Frontend

Ziel: Die vorhandene Pipeline kann ohne Terminal über eine bewusst kleine, ausschließlich lokal erreichbare Oberfläche ausprobiert und präsentiert werden.

| ID | User Story | Abnahmekriterien | Status |
| --- | --- | --- | --- |
| US-030 | Als Nutzer möchte ich ein Bild per Dateiauswahl, Drag-and-drop oder Zwischenablage einfügen, damit besonders Screenshots aus OneNote ohne Pfadarbeit analysiert werden können. | PNG/JPEG werden in einer Bildvorschau angezeigt; Upload und Zwischenablage sind verfügbar; die bestehenden Eingabegrenzen bleiben maßgeblich. | `Erledigt` |
| US-031 | Als Nutzer möchte ich Reinschrift, strukturierte Notizen, automatische Erkennung, Mindmap, Prozess- oder Architekturdiagramm auswählen, damit die bestehende Analyse verständlich steuerbar ist. | Jede UI-Auswahl wird deterministisch auf `Mode` und `requested_type` abgebildet und ist getestet. | `Erledigt` |
| US-032 | Als Nutzer möchte ich das Ergebnis vor dem Speichern sehen, damit verworfene Versuche keinen Ergebnisordner hinterlassen. | Reinschrift, Notizen, lokale SVG-Diagrammgrafik, Mermaid-Quelltext und JSON liegen als Sitzungsvorschau vor; erst Speichern ruft den Writer auf und verursacht keinen zweiten Provideraufruf. | `Erledigt` |
| US-033 | Als Nutzer möchte ich die Datenübertragung weiterhin ausdrücklich bestätigen, damit die lokale Oberfläche den bestehenden Datenschutzvertrag nicht aufweicht. | Ohne Checkbox gibt es bei einem Remote-Provider keinen Request; Gradio-Telemetrie, Sharing, Monitoring und öffentliche Bindung sind deaktiviert. | `Erledigt` |
| US-034 | Als Nutzer möchte ich die Oberfläche mit einem einfachen lokalen Befehl starten, damit sie ohne Frontend-Toolchain vorführbar ist. | `uv run notes2structure-ui` startet auf `127.0.0.1`; README, Paket-Entry-Point und Offline-Tests sind aktualisiert. | `Erledigt` |

Zugeordnete Abnahme: AC-14 und AC-15.

## Empfohlene Reihenfolge

Die Stories werden grundsätzlich nach ihrer Nummer umgesetzt. Das lokale Showcase-Frontend aus
Epic 7 ist als dünner Adapter auf die bestehende Anwendung umgesetzt. Vor einem öffentlichen
Release bleiben insbesondere die geplanten Prüfungen aus Epic 6 relevant.

Erledigte Stories bleiben mit ihrem Status im Backlog erhalten. Ihr automatisierter Nachweis
liegt hauptsächlich in `tests/unit/test_image_reader.py`, `test_pipeline.py`,
`test_renderers.py`, `test_output_writer.py` und `test_cli.py`.
