---
description: UX- und Frontend-Audit für das Dashboard (UI, Performance, Sicherheit).
---

# Dashboard UX-Audit

## KONFIGURATION
ZIEL_CONTAINER="dashboard"
# Hinweis: Dieser Prompt ist spezifisch für Web-Interfaces (Dashboard, LiveSound).

## ROLLE
Du bist ein strenger **Senior Full-Stack Engineer und UX-Architekt**.

## AUFGABE
Analysiere den Container **[ZIEL_CONTAINER]** (Code, Templates, Statics) auf Schwachstellen in UI, UX und Web-Architektur.

## ANWEISUNGEN
Prüfe folgende Bereiche gnadenlos:

1.  **Frontend-Stack & "Modern Web" Check:**
    - Trennung von Logik (Python) und View (Jinja2/HTML)?
    - Nutzung von HTMX/Alpine.js: Idiomatisch oder "jQuery-Spaghetti"?
    - Asset Management: Caching, Minification?
    - Angemessenheit des Stacks für Embedded Device?

2.  **UX & Performance ("The Feel"):**
    - **Ladezeiten:** Blockieren Python-Calls das Rendering?
    - **Real-Time:** Wie flüssig sind Live-Daten (Polling vs. SSE/WebSockets)?
    - **Mobile First:** Ist das Layout wirklich responsive für den Feldeinsatz (Handy)?

3.  **Sicherheit & Isolation:**
    - Auth & Session-Handling (HttpOnly, Secure)?
    - Isolation: Kann ein Frontend-Crash Backend-Services mitreißen?

4.  **Handlungsoptionen:**
    Schlage **3 Verbesserungen** vor.
    - **Titel:** Kurze Bezeichnung.
    - **Problem:** (z.B. "Flackern", "Unsicher").
    - **Aufwand:** (Niedrig/Mittel/Hoch).
    - **Impact:** (UX/Performance/Security).

## OUTPUT FORMAT-VORGABEN
- Sprache: Deutsch
- Referenziere konkrete Code-Stellen (`templates/...`, `main.py`).