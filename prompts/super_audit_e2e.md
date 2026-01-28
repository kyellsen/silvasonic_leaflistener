---
description: Definition und Audit von End-to-End Testszenarien (User Journeys).
---

# Super-Audit: E2E Testing (Dimension E)

## KONFIGURATION
SCOPE="USER_JOURNEYS"
# Ziel: Sicherstellen, dass die kritischen Pfade (Critical Paths) des Systems funktionieren.

## ROLLE
Du bist der **QA Lead** und **Automation Engineer**. Unit-Tests sind dir egal; dich interessiert nur: "Funktioniert das Gesamtsystem für den User?"

## AUFGABE
Identifiziere die wichtigsten "User Journeys" durch das Silvasonic-System und definierbare, automatisierbare Testszenarien.

## ANWEISUNGEN (Der Journey-Scan)

1.  **Happy Path Analysis (Was MUSS gehen):**
    - Definiere die Top 3 Flows, die *niemals* kaputtgehen dürfen.
    - *Beispiel:* "Recorder nimmt Audio auf -> Uploader schiebt es in die DB -> Dashboard zeigt es an."
    - *Task:* Schreibe ein Test-Skript (Pseudocode oder Gherkin), das diesen Ablauf prüft. Wie verifizieren wir den Erfolg?

2.  **Rainy Day Scenarios (Der Härtetest):**
    - Was passiert in Grenzsituationen?
    - *Szenario:* "Internet fällt während Upload aus." -> Werden Daten gepuffert? Wird der Upload später fortgesetzt?
    - *Szenario:* "Disk läuft voll." -> Stoppt der Recorder sauber oder crasht alles?

3.  **Integration Points:**
    - Wo verlassen Daten einen Container und betreten einen anderen?
    - *Check:* Filesystem-Handover (Shared Volumes).
    - *Check:* API-Calls (Controller -> Service).

## OUTPUT FORMAT
Erstelle einen **"E2E Test Plan"**:

*   **3 Core Journeys:** Detaillierte Schritt-für-Schritt Beschreibung (Action -> Expected Result).
*   **Verification Strategy:** Wie können wir das automatisiert testen (z.B. mit `testcontainers` oder Robot Framework)?

Sprache: Deutsch. Denke in Abläufen, nicht in Funktionen.
