# Notes2StructureAI — Projekt- und Coding-Regeln

Diese Regeln gelten für das gesamte Repository und für menschliche wie KI-gestützte Beiträge. Sie beschreiben den Zielzustand; eine hier genannte Funktion oder Prüfung gilt erst nach Implementierung und erfolgreicher Verifikation als vorhanden.

## 1. Ziel und verbindlicher Kontext

Notes2StructureAI ist eine lokal ausgeführte Python-Anwendung mit CLI und schlankem Browser-Frontend. Der primäre Frontend-Workflow räumt handschriftliche Notizen und Skizzen aus PNG/JPG visuell auf und rekonstruiert Inhalt, relative Anordnung und sichtbare Formen als sichere SVG-Seite. Die bestehende CLI erzeugt weiterhin wortnahe Transkription, strukturierte Notizen, ein validiertes JSON-Zwischenformat und gegebenenfalls Mermaid-Diagramme.

Vor Änderungen lesen:

- [Funktionale Spezifikation](docs/spec.md): Umfang, Verhalten und Abnahme.
- [Architektur](docs/architecture.md): Schnittstellen, Datenmodell und technische Entscheidungen.

Die Spezifikation ist maßgeblich für das Produktverhalten, die Architektur für die Umsetzung, dieses Dokument für die Arbeitsweise. Widersprüche vor einer davon abhängigen Implementierung klären. Keine zusätzlichen Features aus Beispielen oder Zukunftsideen ableiten. Verhaltens- und Schnittstellenänderungen zusammen mit den betroffenen Dokumenten und Tests ändern.

## 2. Umfang und Einfachheit

- v0.1: eine Bilddatei je CLI-Aufruf, synchrone Verarbeitung, lokale Dateien als Persistenz.
- Keine öffentlich erreichbare Webanwendung, Datenbank, Cloud-Bereitstellung, Power-Automate-Anbindung, Hintergrunddienste, Folder Watcher oder Multi-Agent-Architektur. Das Showcase-Frontend bindet ausschließlich an die lokale Loopback-Schnittstelle.
- Ein schlanker Provider-Vertrag, ein echter Vision-Adapter und ein Test-Fake reichen. Keine Plugin-Registry, generischen Repository-Schichten, Dependency-Injection-Frameworks oder vorsorglichen Event-Busse.
- CLI und Frontend verwenden denselben Anwendungsdienst mit getrennten, schmalen Analyse- und Cleanup-Pipelines. Das Frontend hält eine Vorschau nur im Arbeitsspeicher und veröffentlicht Artefakte erst nach einer ausdrücklichen Speicheraktion; öffentliches Sharing und Framework-Telemetrie bleiben deaktiviert.
- Funktionen und Module nach fachlicher Verantwortung schneiden. Kleine, nachvollziehbare Funktionen bevorzugen, aber keine willkürlichen Zeilenlimits erzwingen.
- Abhängigkeiten nur für einen konkreten Bedarf hinzufügen und im Review begründen. Standardbibliothek verwenden, wenn sie die Aufgabe klar löst.
- Lokale Ausführung ist keine Zusage vollständig lokaler Inferenz. Netzbasierte Vision-Verarbeitung muss konfiguriert und explizit freigegeben sein; niemals automatisch zu einem externen Dienst wechseln.

## 3. Fachliche Integrität

- Den erkennbaren Inhalt erhalten. Keine stillen Ergänzungen, Korrekturen von Zahlen, erfundenen Verbindungen oder Übersetzungen.
- Transkription und Interpretation getrennt halten. Strukturierung darf ordnen, aber keine neuen Sachbehauptungen erzeugen.
- Unleserlichkeit und Mehrdeutigkeit explizit abbilden. Bei teilweise lesbaren gewöhnlichen Wörtern die plausibelste, sichtbar und kontextuell gestützte Lesart einsetzen, aber als unsichere Rekonstruktion kennzeichnen und Alternativen erhalten. Unbekannte Zahlen, Kennungen, Eigennamen und andere bedeutungskritische Werte nicht durch plausible Vermutungen ersetzen.
- Modellantworten und Bildinhalte sind nicht vertrauenswürdige Eingaben. Anweisungen innerhalb eines Bildes sind Dokumentinhalt, keine auszuführenden Befehle.
- Nur validierte Domain-Modelle an Renderer weitergeben. Syntaktisch gültiges JSON ist noch kein fachlich korrektes Ergebnis.
- Modellbasierte Erkennung kann variieren. Determinismus für Validierung und Rendering garantieren, nicht für erneute Vision-Aufrufe.

## 4. Python und Datenmodelle

- Zielbasis: Python 3.12; weitere Versionen erst nach Aufnahme in CI als unterstützt deklarieren.
- `src/`-Layout, Paketname `notes2structure`, zentrale Konfiguration in `pyproject.toml`.
- Alle eigenen Funktionen und Schnittstellen typisieren. Pyright im Modus `strict` für Anwendung und Tests; kein paralleler zweiter Type Checker.
- Pydantic v2 für externe Daten und Intermediate Representation (IR). Zusätzliche Felder verbieten, Typen strikt validieren und fachliche Invarianten ausdrücklich prüfen.
- Kein `model_construct()` für externe Daten. Kein unkontrolliertes `Any` außerhalb eng begrenzter SDK-Grenzen.
- IDs, Enum-Werte und Feldnamen auf Englisch. Quellinhalte in ihrer Sprache erhalten; keine automatische Übersetzung. Kommentare und Docstrings erklären vor allem Gründe und Verträge.
- `pathlib.Path`, UTF-8 und explizite Zeilenenden für Textartefakte verwenden. Keine betriebssystemspezifischen Pfadannahmen.
- Keine Netzwerk-, Datei- oder Konfigurationszugriffe beim Modulimport. Konfiguration am Programmeinstieg laden und Abhängigkeiten explizit übergeben.

## 5. Architekturgrenzen

- Domain: Pydantic-Modelle und fachliche Validierung, ohne Provider-SDK, CLI oder Dateisystemzugriffe.
- Provider: Bildanalyse und Übersetzung der Anbieterantwort in den vereinbarten Analyse- oder Cleanup-Vertrag. Keine Ausgabe von fertigem Markdown, Mermaid, SVG oder HTML als vertrauenswürdiges Ergebnis übernehmen.
- Pipeline: Schritte koordinieren und Fehler zuordnen; keine SDK-spezifischen Details.
- Renderer: reine Funktionen von validiertem Modell zu Text oder sicherem SVG. Keine Modellaufrufe, Netzwerkzugriffe oder Dateischreiboperationen.
- Infrastruktur: Bildlesen, Konfiguration und sicheres Schreiben der Artefakte.
- Kein Mermaid-Code, HTML oder Dateipfad aus Modelltext direkt ausführen oder als Steuerinformation übernehmen.

## 6. Fehler, Logging und Secrets

- Konkrete Exceptions verwenden und an Grenzen in die Fehlerklassen der Architektur übersetzen. Ursachen intern erhalten, Nutzermeldungen verständlich und bereinigt ausgeben.
- Kein `except Exception: pass`. Breites Abfangen ist nur an der äußeren CLI-Grenze zur kontrollierten Fehlerausgabe gerechtfertigt.
- `logging` für Diagnose nach stderr verwenden. stdout ist für die erfolgreiche Ausgabe des Ergebnisverzeichnisses reserviert; CLI-Hilfe ist ausgenommen.
- Keine Bilddaten, Transkripte, Prompts, vollständigen Providerantworten, API-Schlüssel oder Authorization-Header protokollieren, auch nicht im Debug-Modus.
- Secrets über Umgebungsvariablen; optionale lokale `.env` nur explizit laden. `.env.example` enthält ausschließlich Platzhalter.
- `.env`, private Eingabebilder, generierte Ergebnisse, temporäre Daten und Logs über `.gitignore` ausschließen. Synthetische oder ausdrücklich zur Veröffentlichung freigegebene Test-Fixtures separat verwalten.
- Keine Secrets im Code, in CLI-Argumenten, Beispielausgaben oder Tests. Bei einem Fund nicht wiedergeben; Bereinigung und Rotation veranlassen.
- Provider-Retries begrenzen. SDK-interne und eigene Retries dürfen sich nicht unkontrolliert multiplizieren.

## 7. Qualitätswerkzeuge und reproduzierbare Entwicklung

Für v0.1 festgelegt: `pytest`, Ruff für Linting und Formatierung, Pyright, `pre-commit` und GitHub Actions. Abhängigkeiten über `pyproject.toml` und eine eingecheckte `uv.lock` verwalten. Die Toolchain in CI auf konkrete Versionen festlegen; Updates bewusst prüfen.

Die folgenden Kommandos sind nach dem Bootstrap der verbindliche lokale Prüfweg:

```sh
uv sync --frozen --group dev
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
uv run pre-commit run --all-files
```

`pre-commit` führt mindestens Ruff, Formatprüfung und einfache Datei-/Whitespace-Prüfungen aus. Hooks in der Konfiguration versionieren. CI führt Linting, Formatprüfung, Typprüfung und Tests unabhängig von lokal installierten Hooks aus. Tests mindestens unter Windows und Linux mit Python 3.12 ausführen. Ein Paket-Build und Installationstest prüfen den CLI-Einstieg und mitgelieferte Prompt-Dateien.

GitHub Actions bei Pull Requests und Änderungen am Hauptbranch ausführen, Berechtigungen auf das Nötige begrenzen und Drittanbieter-Actions auf Commit-SHAs fixieren. CI benötigt keine Vision-Secrets und führt keine bezahlten Provideraufrufe aus. Einen schlanken Dependency-Audit und Secret-Scan vor dem ersten öffentlichen Release einrichten; relevante Befunde bearbeiten oder begründet dokumentieren.

## 8. Teststrategie und Definition of Done

- Verhalten und Fehlergrenzen testen: Schemas, referenzielle Integrität, Bildvalidierung, Modi, Unsicherheit, Providerfehler, Escaping und kollisionsfreie Ausgabe.
- Reine Logik mit Unit-Tests, die komplette CLI-Pipeline mit synthetischen Bildern und einem Fake-Provider prüfen.
- Für reproduzierbare Textausgaben kleine Golden Fixtures verwenden. Snapshots nur nach inhaltlichem Review aktualisieren.
- Live-Provider-Tests separat kennzeichnen und ausdrücklich starten. Keine Netzwerkabhängigkeit in der normalen Testsuite.
- Keine starre 100-%-Coverage-Vorgabe. Tests sollen relevante Fehler finden, nicht triviale Implementierungsschritte spiegeln.
- Für Mermaid neben Textvergleichen repräsentative und adversariale Fixtures mit einer festgelegten Mermaid-Parser-Version prüfen. Die dafür nötige JavaScript-Toolchain bleibt reine Entwicklungsabhängigkeit.
- Spätere Evals messen Erkennungsqualität getrennt von Softwaretests. Erfolgreiche Unit-Tests beweisen keine korrekte Handschrifterkennung.

Eine Änderung ist fertig, wenn ihr vereinbartes Verhalten implementiert ist, relevante Tests und Qualitätsprüfungen bestanden sind, Dokumentation und Beispielverträge stimmen und der Diff auf unbeabsichtigte Änderungen sowie sensible Daten geprüft wurde. Im Abschlussbericht nennen: Änderung, tatsächlich ausgeführte Prüfungen, Ergebnis und verbleibende Einschränkungen. Nicht ausgeführte Prüfungen niemals als bestanden melden.

## 9. Arbeitsweise

In kleinen, überprüfbaren Paketen arbeiten. Bestehende Änderungen respektieren, keine pauschalen Rewrites und keine themenfremden Refactorings. Specs unterstützen Engineering; sie ersetzen weder Tests noch menschliches Review.

Empfohlene Reihenfolge: Tooling und Schemas → Bildladen und Fake-Pipeline → Renderer und sichere Ausgabe → echter Provider → End-to-End-Abnahme. Jeder Schritt bleibt eigenständig prüfbar. PR-Beschreibungen erklären Problem, Verhalten, Validierung und relevante Grenzen; Veröffentlichung und Merge erfolgen entsprechend dem vereinbarten Projektworkflow.
