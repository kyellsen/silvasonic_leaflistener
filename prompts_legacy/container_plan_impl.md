---
description: Erstellt einen konkreten Implementierungsplan für eine ausgewählte Refactoring-Option.
---

# Container Implementierungs-Plan

## KONFIGURATION
ZIEL_CONTAINER="recorder"  
# Mögliche Werte: "db", "gateway", "controller", "healthchecker", "recorder", "weather", "birdnet", "livesound", "uploader", "dashboard"

GEWAEHLTE_AUFGABE="[HIER EINFÜGEN WAS DU MACHEN WILLST, Z.B. 'Option B: Einführung von Structlog']"

## ROLLE
Du bist Lead Developer im Silvasonic-Projekt.

## AUFGABE
Erstelle einen detaillierten **Implementierungsplan** (Step-by-Step Guide), um die Aufgabe **"[GEWAEHLTE_AUFGABE]"** für Container **[ZIEL_CONTAINER]** sicher umzusetzen.

## ANWEISUNGEN
Strukturiere den Plan wie folgt:

1.  **Vorbereitung & Dependencies:**
    - `pyproject.toml` (Libraries hinzufügen/entfernen?)
    - `Dockerfile` (Anpassungen nötig?)

2.  **Code- und Architektur-Änderungen:**
    - Beschreibe die Änderungen Schritt für Schritt.
    - Was muss gelöscht werden? (Legacy Code: Kill it, don't migrate!)

3.  **Risiko-Minimierung & Tests:**
    - Wie stellen wir sicher, dass nichts bricht?

## GUIDELINES
- Wir sind in der MVP/Prototyp Phase.
- Keine komplexen Migrationen.
- Im Zweifel: Container neu aufbauen statt Legacy patchen.

## OUTPUT FORMAT-VORGABEN
- Sprache: Deutsch
- Format: Liste / Markdown Checkboxen
