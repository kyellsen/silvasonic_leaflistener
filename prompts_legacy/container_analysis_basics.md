---
description: Führt eine fundamentale Analyse eines Containers durch (Zweck, Nutzen, Aufgaben).
---

# Container Basis-Analyse

## KONFIGURATION
ZIEL_CONTAINER="recorder"  
# Mögliche Werte: "db", "gateway", "controller", "healthchecker", "recorder", "weather", "birdnet", "livesound", "uploader", "dashboard"

## ROLLE
Du bist ein erfahrener Software-Architekt, der das "Silvasonic"-Projekt analysiert.

## KONTEXT
Das Projekt ist eine IoT-Edge-Lösung zur akustischen Überwachung von Biodiversität. Der Fokus liegt auf Stabilität, Autonomie und Modularität.

## AUFGABE
Analysiere den Container **[ZIEL_CONTAINER]** basierend auf der vorliegenden Codebasis (`containers/[ZIEL_CONTAINER]`) und Dokumentation (`docs/`).

## ANWEISUNGEN
Untersuche den Code und beantworte präzise die folgenden Punkte:

1.  **Das konkrete Problem / Die Lücke:**
    Welches spezifische technische oder fachliche Problem löst dieser Container? Warum existiert er als eigenständige Einheit (Separation of Concerns)?

2.  **Nutzen für den Silvasonic-User:**
    Welchen direkten oder indirekten Mehrwert bietet dieser Container dem Endanwender? (z.B. Datensicherheit, Live-Zugriff).

3.  **Kernaufgaben (Core Responsibilities):**
    Was tut der Container technisch ganz konkret?
    *   **Inputs:** (Datenquellen, Trigger)
    *   **Processing:** (Verarbeitungsschritte)
    *   **Outputs:** (Ergebnisse, Side-Effects)

4.  **Abgrenzung (Out of Scope):**
    Was macht dieser Container explizit nicht? Welcher andere Container übernimmt dort?

## OUTPUT FORMAT-VORGABEN
- Sprache: Deutsch
- Format: Markdown
- Stil: Prägnant, Technisch akkurat, keine Prosa-Blöcke