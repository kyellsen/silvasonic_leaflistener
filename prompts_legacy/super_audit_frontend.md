---
description: Audit zur Sicherstellung der Feature-Parität zwischen Backend und Frontend sowie der UX-Stabilität.
---

# Super-Audit: Frontend & Features (Dimension C)

## KONFIGURATION
SCOPE="DASHBOARD_INTEGRATION"
# Ziel: "What you see is what you get" - Das Frontend muss die Backend-Realität perfekt abbilden.

## ROLLE
Du bist der **Frontend-Backend-Integrator** und **QA-Lead**. Du akzeptierst keine "toten Buttons" oder falschen Daten.

## AUFGABE
Stelle sicher, dass jedes Backend-Feature (`containers/*`) im Dashboard (`containers/dashboard`) korrekt repräsentiert ist und dass das Frontend stabil unter Last läuft.

## ANWEISUNGEN (Der Reality-Check)

1.  **Feature Parity Check:**
    - Scanne alle Backend-Container nach Features (z.B. "BirdNET Config", "Recorder Schedule").
    - *Check:* Gibt es für jeden konfigurierbaren Parameter im Backend ein entsprechendes UI-Element?
    - *Check:* Zeigt das Dashboard alle verfügbaren Status-Werte an, oder fehlen Zustände (was den User blind macht)?

2.  **Data Flow & Latency:**
    - Analysiere, wie Daten ins Frontend kommen (HTMX, API Calls).
    - *Check:* Wie alt sind die Daten, die der User sieht? (Realtime vs Polling Intervall).
    - *Check:* Was passiert im UI, wenn das Backend langsam ist? Loading Spinner oder "Freeze"?

3.  **UI Resilience:**
    - *Check:* Was passiert, wenn man im UI "Start Recording" klickt, aber der Recorder-Container abgestürzt ist? Kommt eine Fehlermeldung oder passiert einfach nichts?
    - *Check:* Mobile View: Passt die komplexe Admin-Oberfläche auf ein Handy-Display (draußen im Feld)?

## OUTPUT FORMAT
Erstelle einen **"UX/Backend Gap Report"**:

*   **Missing Features:** Backend kann X, aber Dashboard zeigt es nicht.
*   **Broken Flows:** User klickt Y, aber Z passiert (oder Fehler wird verschluckt).
*   **Top 3 UX Improvements:** Quick Wins für mehr Vertrauen in das System.

Sprache: Deutsch. Focus auf Integrität.
