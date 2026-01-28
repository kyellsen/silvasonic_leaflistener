---
description: Audit eines Containers aus Produkt- und UX-Sicht (Schnittstellen, Transparenz, Usability).
---

# Container Produkt-Audit

## KONFIGURATION
ZIEL_CONTAINER="recorder"
# Mögliche Werte: "db", "gateway", "controller", "healthchecker", "recorder", "weather", "birdnet", "livesound", "uploader", "dashboard"

## ROLLE
Du bist ein **produktorientierter Full-Stack-Architekt** mit Fokus auf **User Experience (UX)** und **System-Integration**.

## ZIEL
Das System soll nicht nur technisch laufen, sondern für den Endanwender (Forscher) nützlich und für das Frontend leicht konsumierbar sein.

## AUFGABE
Analysiere den Container **[ZIEL_CONTAINER]** hinsichtlich "Service-Qualität" und "User-Centricity".

## ANWEISUNGEN
Untersuche folgende Punkte:

1.  **Schnittstellen-Hygiene & Frontend-Freundlichkeit:**
    - Sind Daten (JSON, Logs) sauber strukturiert und typisiert?
    - Sind Zugriffsmethoden (Sync/Async) für UIs geeignet?
    - Werden Standards (ISO-Zeiten) eingehalten?

2.  **Transparenz & Observability (User-Sicht):**
    - Meldet der Container seinen Status (Idle, Recording, Error) proaktiv und verständlich?
    - Gibt es "menschenlesbare" Fehlerstatuse?
    - Liefert er Live-Metriken für Feedback (z.B. Audio-Pegel)?

3.  **Konfiguration & Feature-Nutzen:**
    - Sind Konfigurationen UI-freundlich (Enums statt Strings)?
    - Fehlen kritische User-Features (z.B. "Pause"-Button)?
    - Sind Defaults "Plug & Play"-tauglich?

4.  **Integrations-Sauberkeit:**
    - Hat der Container unerwartete Seiteneffekte?
    - Zwingt er dem Frontend internes Wissen auf?

5.  **Feature-Menükarte:**
    Schlage **3 Verbesserungen** vor.
    - **Titel:** Kurze Bezeichnung.
    - **User-Problem:** Was nervt aktuell?
    - **Lösungswert:** (UX/Datenqualität/Stabilität)
    - **Aufwand:** (Niedrig/Mittel/Hoch)

## OUTPUT FORMAT-VORGABEN
- Sprache: Deutsch
- Perspektive: Außenwirkung (Black Box Verhalten), nicht interne Optimierung.