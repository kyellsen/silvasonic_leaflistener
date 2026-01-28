---
description: Erstellt die initiale Dokumentationsstruktur für alle Container.
---

# Container Doku-Generator

## KONFIGURATION
# Geltungsbereich: Alle Unterordner in `containers/`

## ROLLE
Du bist der **Technical Documentation Lead** für das Silvasonic-Projekt.

## AUFGABE
Erstelle für **JEDEN** Container im Verzeichnis `containers/` eine Dokumentationsdatei in `docs/containers/`.

## ANWEISUNGEN
1.  **Scan:** Identifiziere alle Container (db, gateway, controller, healthchecker, recorder, weather, birdnet, livesound, uploader, dashboard).
2.  **Verzeichnis:** Erstelle `docs/containers/` (falls fehlend).
3.  **Dokument:** Erstelle `docs/containers/[CONTAINER_NAME].md` basierend auf Code-Analyse.

## STRUKTUR PRO DATEI (Template)
Jede `.md` Datei muss exakt diese Struktur haben:

```markdown
# Container: [Name]

## 1. Das Problem / Die Lücke
Welches spezifische Problem löst dieser Container?

## 2. Nutzen für den User
Was bringt es dem Endanwender?

## 3. Kernaufgaben (Core Responsibilities)
Technische Fakten basierend auf Code-Analyse (Python/Dockerfile).
* Inputs: (Datenquellen)
* Processing: (Was passiert?)
* Outputs: (Ergebnisse)

## 4. Abgrenzung (Out of Scope)
Was macht dieser Container NICHT?
```

## GUIDELINES
- Analysiere den existierenden Code. Rate nicht.
- Sprache: Deutsch.
- Überschreibe existierende Dateien um das Format durchzusetzen.