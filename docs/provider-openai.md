# Providerentscheidung für v0.1: OpenAI

## Entscheidung

Notes2StructureAI verwendet in v0.1 den OpenAI-Provider mit dem Modell
`gpt-5.6-terra` über die Responses API. Die Python-Abhängigkeit ist auf `openai==3.14.1`
festgelegt. Das Modell akzeptiert Bildeingaben und unterstützt strukturierte Ausgaben. Die
Anwendung übermittelt Bilder als Base64-Daten-URL mit Detailstufe `original` und lässt die
Antwort direkt gegen das strenge Pydantic-Modell `AnalysisPayload` erzeugen.

Offizielle Referenzen:

- [Modell gpt-5.6-terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra)
- [Bildeingaben und Detailstufen](https://developers.openai.com/api/docs/guides/images-vision)
- [Strukturierte Ausgaben](https://developers.openai.com/api/docs/guides/structured-outputs)
- [API-Datenkontrollen](https://platform.openai.com/docs/guides/your-data)

## Übertragung und Datenschutzgrenze

Ohne CLI-Schalter `--allow-remote` findet kein Provideraufruf statt. Übertragen werden nur
das lokal dekodierte, EXIF-bereinigte und als RGB-PNG neu kodierte Bild, der versionierte
Analyse-Prompt, Modus und optionale Typvorgabe. Lokale Dateipfade und der ursprüngliche
Dateiname sind nicht Teil des Requests. `store=False` verhindert das Speichern der Response
als API-Anwendungszustand. Laut OpenAI werden API-Daten standardmäßig nicht zum Training
verwendet; abhängig von Kontoeinstellungen und rechtlichen Anforderungen können
Missbrauchsprotokolle zeitlich begrenzt aufbewahrt werden. Die aktuelle OpenAI-Dokumentation
bleibt dafür maßgeblich.

Im lokalen Frontend entspricht die Checkbox zur Bildübertragung dem CLI-Schalter. Sie ist beim
Start deaktiviert und muss vor der Analyse bewusst gesetzt werden. Die Vorschau oder das
Verwerfen ändert nichts daran, dass der Provideraufruf zu diesem Zeitpunkt bereits erfolgt ist.

## Secret und Konfiguration

Erforderlich sind `N2S_PROVIDER=openai`, `N2S_MODEL=gpt-5.6-terra` und `N2S_API_KEY`.
Konfiguration kommt entweder aus bereits gesetzten Umgebungsvariablen oder aus einer mit
`--env-file` ausdrücklich genannten Datei. Umgebungsvariablen haben Vorrang. Es gibt keine
automatische `.env`-Suche und keinen API-Key als CLI-Argument. Fehlermeldungen geben weder
Schlüssel noch Providerantworten wieder.

## Ressourcen- und Fehlergrenzen

- maximal ein Request im Normalfall und drei Gesamtversuche bei Verbindung, Timeout, HTTP 429
  oder HTTP 5xx;
- SDK-eigene Retries deaktiviert, 60 Sekunden je Versuch und 200 Sekunden Gesamtfrist;
- Backoff von 1 und 2 Sekunden mit kleinem Jitter; `Retry-After` nur innerhalb der Gesamtfrist;
- höchstens 2 MiB Antwortdaten vor dem Parsing;
- kein Reparaturaufruf, Modell-Fallback oder paralleler Request;
- strengere Bildgrenzen des Modells werden vor der Übertragung geprüft.

Ein Timeout kann eintreten, nachdem OpenAI die Anfrage bereits verarbeitet hat. Deshalb kann
ein Wiederholungsversuch zusätzliche Kosten verursachen; Exactly-once-Verarbeitung wird nicht
versprochen.

## Bekannte Grenzen

Handschrifterkennung bleibt probabilistisch. Erfolgreiche Softwaretests belegen weder korrekte
Transkription noch korrekte Beziehungen einer Skizze. Reale, ausdrücklich freigegebene Bilder
müssen deshalb vor dem Release manuell mit den Ergebnissen verglichen werden. Außerdem setzt
die Nutzung ein OpenAI-Projekt mit aktivierter API-Abrechnung und Modellzugriff voraus.
