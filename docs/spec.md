# Notes2StructureAI — Spezifikation v0.1

Status: implementierbarer MVP-Vertrag. Diese Datei beschreibt Anforderungen, keinen bereits erreichten Implementierungsstand. Projektregeln stehen in [AGENTS.md](../AGENTS.md), technische Verträge in [architecture.md](architecture.md).

## 1. Ziel

Ein Nutzer startet lokal einen CLI-Aufruf für eine handschriftliche Notiz oder Skizze. Das Programm erzeugt überprüfbare digitale Artefakte und erhält die Unterscheidung zwischen erkanntem Inhalt und Interpretation. Das Originalbild bleibt unverändert.

Der MVP unterstützt deutsche und englische Handschrift sowie gemischte Beschriftungen. Er bewahrt die Quellsprache und macht Unsicherheiten sichtbar. Er garantiert weder fehlerfreie Erkennung noch fachliche Richtigkeit einer Interpretation.

## 2. Umfang und Grundentscheidungen

- Eine Bilddatei je Aufruf, keine Verzeichnisverarbeitung und kein Hintergrundbetrieb.
- Lokale CLI, lokale Konfiguration und lokale Ergebnisse; keine Bereitstellung eines Servers.
- Ein Vision-Provider mit einem konkreten Adapter für v0.1. Anbieter und Modell werden bei Implementierung dieses Adapters festgelegt, konfiguriert und dokumentiert; kein versteckter Standardanbieter.
- Eine externe Vision-API ist optional zulässig. Vor jeder externen Übertragung muss `--allow-remote` gesetzt sein. Ohne dieses Flag sind externe Requests verboten. Ein lokales Modell ist ein späterer Erweiterungspunkt und kein MVP-Versprechen.
- Ohne konfigurierten echten Provider ist reale Bilderkennung nicht verfügbar. Ein Fake dient ausschließlich Tests und ist kein Erkennungsersatz.
- JSON ist die gemeinsame Quelle aller Text- und Diagrammausgaben; das Modell erzeugt keine direkt übernommenen Ausgabedateien.

## 3. CLI und Modi

Verbindlicher CLI-Vertrag; ein Paket-Entry-Point stellt `notes2structure` bereit:

```sh
notes2structure analyze sketch.png --output-dir output --mode full --document-type auto
```

Für einen konfigurierten externen Provider wird ausdrücklich `--allow-remote` ergänzt. `--output-dir` hat den Standardwert `./output`, `--mode` den Standardwert `full`, `--document-type` den Standardwert `auto`. Provider und Modell kommen aus der validierten Umgebungskonfiguration. API-Schlüssel werden nicht als CLI-Argumente angenommen.

| Modus | Erkennung und verpflichtende Dateien |
| --- | --- |
| `transcribe` | Wortnahe Transkription und Unsicherheiten; `result.json`, `transcript.md`. Keine Klassifikation, keine Strukturierung, kein Diagramm. |
| `full` | Transkription, Strukturierung, Klassifikation und geeignete Diagrammdaten; `result.json`, `transcript.md`, `notes.md`; `diagram.mmd` nur bei nutzbarem Graph. |

`--document-type` akzeptiert `auto`, `notes`, `mindmap`, `process`, `architecture`. Eine Vorgabe ist ein Interpretationshinweis, keine Erlaubnis, fehlende Strukturen zu erfinden. Das Ergebnis hält erkannte und gewünschte Klassifikation getrennt fest. In `transcribe` ist nur `auto` zulässig; andere Kombinationen sind Aufruffehler.

Der erfolgreiche Aufruf schreibt genau den Pfad des fertigen Ergebnisverzeichnisses nach stdout. Diagnose und Warnungen gehen nach stderr. `--help` beschreibt die Modi, die mögliche Bildübertragung und Konfigurationsvariablen.

## 4. Eingaben

**IN-01:** Unterstützt werden PNG und JPEG (`.png`, `.jpg`, `.jpeg`, Groß-/Kleinschreibung irrelevant), jeweils ein statisches Bild. Tatsächliches Dateiformat und Dekodierbarkeit prüfen; Endung allein genügt nicht. Endung und erkanntes Format müssen übereinstimmen, `.jpg` und `.jpeg` sind gleichwertig.

**IN-02:** MVP-Grenzen: maximal 20 MiB Dateigröße und 25 Millionen Pixel. Animierte oder mehrseitige Dateien, ungültige Bilddaten, leere Dateien und unlesbare Pfade vor einem Provideraufruf zurückweisen. Die Dekodierung muss die Pixelgrenze berücksichtigen.

**IN-03:** EXIF-Orientierung anwenden, Transparenz auf Weiß auflösen und für den Provider RGB-Bilddaten ohne EXIF/GPS-Metadaten neu kodieren. Keine automatische Skalierung, Beschneidung oder verlustbehaftete Bildverbesserung im MVP. Strengere Anbietergrenzen vor Übertragung prüfen und verständlich melden.

**IN-04:** Hash des ursprünglichen Dateiinhalts, ursprünglichen Basisdateinamen und normalisierte Bildabmessungen lokal in der IR speichern. Keine absoluten Eingabepfade oder Originalbilder in die Ergebnisse kopieren. Die einzige Dateiübertragung betrifft das normalisierte Bild und den für die Analyse benötigten Prompt.

## 5. Funktionale Anforderungen

### 5.1 Transkription

**FR-01:** Lesbaren Text möglichst wortnah und ohne stilistische Glättung wiedergeben. Rechtschreibung, Zahlen und Eigennamen nicht still korrigieren. Erkennbare Zeilen oder räumliche Gruppen in einer plausiblen Lesereihenfolge als Segmente erfassen; kein pixelgenaues Layout rekonstruieren.

**FR-02:** Jedes Segment erhält eine lokale ID, seinen Text und den Status `clear`, `uncertain` oder `unreadable`. Vollständig unlesbare Segmente enthalten den Platzhalter `[unleserlich]`, teilunlesbare Textstellen denselben Platzhalter innerhalb des Textes. Unsichere Lesarten und Alternativen gehören zusätzlich in die Unsicherheitsliste. Markdown zeigt die IDs, Status und Hinweise, sodass keine unsichere Lesart wie gesicherter Text erscheint.

### 5.2 Strukturierte Notizen

**FR-03:** Im Modus `full` Inhalte in geordnete Abschnitte mit Überschrift und Notizpunkten gliedern. Inhalte dürfen umgeordnet und sprachlich verdichtet werden; jede inhaltliche Aussage muss auf Transkriptsegmente zurückverweisen. Keine zusätzlichen Empfehlungen, Aufgaben, Fristen oder Schlussfolgerungen erzeugen.

**FR-04:** Überschriften als Strukturierung kennzeichnen; sie sind kein wortwörtliches Zitat. Unsicherheiten der referenzierten Segmente in `notes.md` bei den betroffenen Notizpunkten anzeigen. Inhalte, die nur visuell durch Formen oder Pfeile belegt sind, gehören in den Graphen und dessen Evidenzangaben.

### 5.3 Klassifikation

**FR-05:** Im Modus `full` einen erkannten Typ aus `notes`, `mindmap`, `process`, `architecture`, `unknown` mit kurzer Begründung liefern. `unknown` ist der ausdrückliche Rückfallwert für unklare oder gleichrangig gemischte Dokumente; keine erzwungene Sicherheit.

| Typ | Erkennbare Struktur |
| --- | --- |
| `notes` | Freitext, Listen oder lose Notizen ohne dominante Diagrammstruktur |
| `mindmap` | Zentrales Thema mit hierarchisch angeordneten Unterthemen |
| `process` | Ablauf, Schritte, Entscheidungen oder gerichtete Übergänge |
| `architecture` | Komponenten, Systeme oder Schnittstellen und ihre Beziehungen |
| `unknown` | Keine belastbare Zuordnung oder kein klar dominanter Typ |

**FR-06:** Eine Benutzervorgabe als `requested_type` speichern. `effective_type` entspricht der Vorgabe, falls vorhanden, sonst dem erkannten Typ. Eine Abweichung vom erkannten Typ wird sichtbar gewarnt. Eine Vorgabe ergänzt keine fehlenden Knoten oder Kanten. Im Transkriptionsmodus sind alle drei Typfelder `null`.

### 5.4 JSON und Diagramme

**FR-07:** `result.json` enthält die schema-versionierte, vollständig validierte IR aus der Architektur. Metadaten, Quellreferenzen, Unsicherheiten und den Diagrammstatus einschließen. Keine rohe SDK-Antwort als IR speichern.

**FR-08:** Für `mindmap`, `process` und `architecture` bei mindestens einem belegten Knoten Mermaid erzeugen. Alle drei Typen werden im MVP als einfache Flowcharts dargestellt: Mindmaps hierarchisch als `flowchart TD`, Prozesse als `flowchart TD`, Architektur als `flowchart LR`. Native Mermaid-Mindmap-, BPMN-, UML- oder C4-Semantik ist nicht zugesagt.

**FR-09:** `notes` und `unknown` erhalten kein Diagramm. Fehlende oder nicht belastbar extrahierbare Diagrammstruktur führt zu einem erfolgreichen Ergebnis mit `diagram.status = "omitted"` und nachvollziehbarem Grund. Niemals ein leeres oder erfundenes Diagramm erzeugen.

**FR-10:** Unsichere Knoten und Kanten im Diagramm explizit mit `(?)` kennzeichnen; unsichere Kanten zusätzlich gestrichelt darstellen. Unbekannte Pfeilrichtung als ungerichtete Beziehung abbilden. Keine Verbindungen allein aus räumlicher Nähe als gesichert ausgeben.

**FR-11:** Mermaid ausschließlich aus dem validierten Graphen erzeugen. Labels sicher kodieren; Modelltext darf weder Mermaid-Direktiven, HTML, Links, Klickaktionen noch zusätzliche Statements einschleusen. Markdown enthält keine ausführbaren HTML-Inhalte. Sonderzeichen erhalten, soweit sicher darstellbar; jede notwendige Ersetzung ist deterministisch.

## 6. Unsicherheit und menschliche Prüfung

Jede Unsicherheit besitzt ID, Art (`text`, `classification`, `structure`, `relation`), betroffene Objekt-IDs oder das Ziel `classification`, eine konkrete Erklärung und optional alternative Lesarten. Statuswerte sind qualitative Modellurteile, keine kalibrierten Wahrscheinlichkeiten.

- Unlesbarer Text wird nicht ergänzt; alternative Lesarten bleiben als Alternativen sichtbar.
- Aus sichtbarem Text abgeleitete Notizpunkte und Graphknoten übernehmen dessen Unsicherheit.
- Mehrdeutige Pfeile erhalten eine Erklärung; nicht belegbare Beziehungen werden ausgelassen.
- Ein leeres oder vollständig unleserliches, technisch gültiges Bild ist kein Programmfehler: leere Inhalte oder unleserliche Segmente, `unknown` im Modus `full`, kein Diagramm und ein sichtbarer Warnhinweis.
- `review_required` ist wahr, sobald Unsicherheiten, unsichere/unleserliche Segmente oder Graphobjekte, ein Typkonflikt oder ein ausgelassenes erwartetes Diagramm vorliegen; im Modus `full` außerdem bei `unknown`, in beiden Modi bei fehlendem lesbarem Text. Andernfalls ist es falsch. Dieses Flag ersetzt keine Genauigkeitsgarantie.
- Beide Markdown-Dateien zeigen den Prüfstatus und relevante Hinweise. Das Programm fragt nicht interaktiv nach Korrekturen; manuelles Review der Dateien genügt im MVP.

## 7. Ausgabevertrag und Fehler

Jeder erfolgreiche Lauf erzeugt unter `--output-dir` ein neues Verzeichnis `run-<uuid4-hex>`. Namen von Ausgabedateien sind fest vorgegeben. Niemals vorhandene Ergebnisse ersetzen und nie Dateinamen aus Modelltext ableiten.

Artefakte zunächst in einem temporären Geschwisterverzeichnis vollständig schreiben und erst dann per Umbenennung veröffentlichen. Bei einem Fehler erscheint kein vollständiges Ergebnisverzeichnis; alte Ergebnisse bleiben erhalten. Temporäre Reste nach einem Prozessabbruch sind möglich und klar als temporär benannt. UTF-8, LF und ein abschließender Zeilenumbruch gelten für alle Textdateien.

| Exitcode | Bedeutung |
| --- | --- |
| `0` | Ergebnis vollständig gespeichert; fachliche Unsicherheit wird in Artefakten und stderr kenntlich gemacht |
| `2` | Ungültiger Aufruf, Konfiguration oder Eingabe; fehlende Freigabe externer Übertragung |
| `3` | Providerfehler, Authentifizierung, Timeout oder ausgeschöpfte Retries |
| `4` | Ungültige Providerstruktur oder verletzte IR-Invarianten |
| `5` | Renderer- oder Ausgabefehler |
| `1` | Unerwarteter interner Fehler mit bereinigter Fehlermeldung |

Keine halbfertigen Fachartefakte bei technischem Fehlschlag. Unsicherheit ist ein fachliches Ergebnis; unparsebares oder ungültiges Modell-JSON ist ein technischer Fehler und wird nicht still repariert.

## 8. Nichtfunktionale Anforderungen

**NFR-01 — Wartbarkeit:** Typed Python, modulare Verantwortlichkeiten, eine synchrone Pipeline, explizite Konfiguration. Technische Details und Qualitätskommandos stehen in den beiden Begleitdokumenten.

**NFR-02 — Reproduzierbarkeit:** Gleiche validierte IR erzeugt byteidentische Markdown-/Mermaid-Dateien. Neue Modellaufrufe dürfen abweichen. Modellkennung, Provider, Prompt-Version und Schema-Version zur Nachvollziehbarkeit speichern.

**NFR-03 — Datenschutz:** Keine Telemetrie, keine externen Requests ohne Freigabe, keine sensiblen Inhalte in Logs, keine eingebetteten Metadaten übertragen. Eigene Dateien in synchronisierten Verzeichnissen unterliegen weiterhin der vom Nutzer eingerichteten Synchronisierung. Die Anwendung steuert keine Speicher- oder Trainingsrichtlinien des gewählten Anbieters; diese sind bei dessen Einrichtung zu dokumentieren.

**NFR-04 — Begrenzte Ressourcen:** Ein Provideraufruf pro Analyse als Normalfall. Höchstens drei Gesamtversuche bei transienten Fehlern, maximal 60 Sekunden je Versuch und 200 Sekunden Gesamtdauer einschließlich Wartezeit. Providerantworten vor Parsing auf 2 MiB begrenzen. Keine parallele Verarbeitung, automatischen Reparaturaufrufe oder versteckten Modell-Fallbacks.

**NFR-05 — Portabilität:** Windows und Linux mit Python 3.12 durch CI absichern; Pfade mit Leerzeichen und Unicode unterstützen. Mermaid-Bildexport benötigt keine Runtime-Abhängigkeit, da v0.1 nur `.mmd` ausgibt.

**NFR-06 — Qualität:** Offline-Tests, Ruff, strenge Typprüfung und CI sind Release-Voraussetzungen. Semantische Erkennungsqualität zusätzlich manuell an kleinen, freigegebenen Beispielen prüfen; daraus keine unbelegte Genauigkeitsquote ableiten.

## 9. Acceptance Criteria

Die Abnahme kombiniert automatisierte Softwaretests mit einem kleinen Live-Smoke-Test. Fake-Provider prüfen Verträge, nicht die tatsächliche Erkennungsqualität.

| ID | Szenario und überprüfbares Ergebnis |
| --- | --- |
| AC-01 | Gültiges PNG und JPEG werden im Modus `full` mit Fake-Provider verarbeitet: Exit `0`, drei Pflichtdateien, gültige IR und unveränderte Quelldatei. |
| AC-02 | `transcribe` erzeugt genau zwei Pflichtdateien, leere Struktur-/Graphfelder, keine Klassifikation und kein Diagramm; eine Typvorgabe wird mit Exit `2` abgelehnt. |
| AC-03 | Synthetische Fixtures decken alle fünf erkannten Typen ab. Diagrammtypen erzeugen bei nutzbarem Graph `.mmd`, `notes`/`unknown` nicht. |
| AC-04 | Unleserliche Segmente, mehrdeutige Zahlen, unsichere Kanten und Typkonflikte bleiben in JSON und Markdown sichtbar; Graphunsicherheit erscheint auch in Mermaid. `review_required` stimmt. |
| AC-05 | Fehlender Pfad, kaputtes Bild, Formatkonflikt, Animation und überschrittene Eingabegrenzen führen vor einem Provideraufruf zu Exit `2`. EXIF-Orientierung, Transparenz und Metadatenentfernung sind geprüft. |
| AC-06 | Fehlende Remote-Freigabe verursacht null Requests und Exit `2`. Geheime Konfiguration und Dokumentinhalte erscheinen in keinem Log. |
| AC-07 | Ungültiges JSON, falsche Typen, Zusatzfelder, doppelte IDs und verwaiste Referenzen führen zu Exit `4`, ohne fertiges Ergebnisverzeichnis. |
| AC-08 | Timeout, Rate Limit, Authentifizierungsfehler und transiente Serverfehler sind simuliert. Retry- und Zeitlimits gelten, nicht wiederholbare Fehler werden nicht erneut gesendet. |
| AC-09 | Wiederholte Läufe überschreiben nichts. Simulierte Schreib-/Rendererfehler ergeben Exit `5`; bestehende Ergebnisse bleiben erhalten. Pfade mit Leerzeichen und Unicode funktionieren. |
| AC-10 | Rendering derselben IR ist byteidentisch. Labels mit Anführungszeichen, Klammern, Unicode, Zeilenumbrüchen und Einschleusungsversuchen bestehen die Mermaid-Parser-Prüfung und erzeugen keine aktiven Inhalte. |
| AC-11 | Leeres, unleserliches oder strukturarmes Bild liefert ein überprüfbares Ergebnis mit Warnung; keine erfundenen Knoten/Kanten und kein vorgetäuschtes Diagramm. |
| AC-12 | Lint-, Format-, Typ-, Test- und Paketprüfungen sind in CI erfolgreich; die normale Testsuite benötigt weder Netz noch API-Schlüssel. |
| AC-13 | Vor v0.1-Abnahme mindestens ein freigegebenes Bild pro Kern-Dokumenttyp sowie ein schwieriges Beispiel mit echtem Provider prüfen. Transkription, Zahlen, Klassifikation, Beziehungen und Unsicherheiten mit dem Original vergleichen; beobachtete Fehler und Modell-/Prompt-Version dokumentieren. |

## 10. Out of Scope und spätere Optionen

Nicht Teil von v0.1: Folder Watcher, Batch-Verarbeitung, mehrseitige Dokumente/PDF, Kameraaufnahme, OCR-Trainingspipeline, Handschrifterkennungstraining, GUI/Web-App, Datenbank, Benutzerverwaltung, Cloud-Deployment, Power Automate, Agenten-Orchestrierung, Diagrammeditor, automatische Aktionen aus erkannten Notizen, SVG/PNG/PDF-Export und Volltextsuche.

Später denkbar: lokaler Vision-Adapter, Batch-/Watcher-Adapter, manuell korrigierbare IR, zusätzliche Renderer und ein versionierter Eval-Datensatz. Diese Optionen begründen keine vorsorgliche Infrastruktur im MVP.
