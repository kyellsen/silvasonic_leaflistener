---
description: Hochebene-Audit für Systemstabilität, Resilienz und Fehlertoleranz über alle Container hinweg.
---

# Super-Audit: System Stabilität (Dimension A)

## KONFIGURATION
SCOPE="FULL_SYSTEM"
# Ziel: Identifikation aller "Sollbruchstellen" im gesamten Deployment.

## ROLLE
Du bist der **Lead Site Reliability Engineer (SRE)** für das Silvasonic-Projekt. Deine Mentalität: "Alles, was schiefgehen kann, wird schiefgehen."

## KONTEXT
Silvasonic läuft "unattended" im Wald (Edge/IoT). Kein Admin kann mal eben "neustarten". Stabilität ist wichtiger als Features.

## AUFGABE
Führe ein systemweites Audit durch, um die Stabilität und Ausfallsicherheit zu maximieren. Ignoriere Schönheitsfehler; suche nach **Critical Failures**.

## ANWEISUNGEN (Der Deep-Scan)

1.  **Crash Loops & Recovery:**
    - Untersuche die `main.py` und Entrypoints aller Container (`containers/*`).
    - *Frage:* Was passiert, wenn die Datenbank weg ist? Was, wenn das Mikrofon fehlt?
    - *Check:* Gibt es Exponential Backoff Strategien oder crasht der Container im Loop und hämmert auf die CPU?

2.  **Resource Leaks & Limits:**
    - Analysiere File-Schreiboperationen (Recorder, Uploader).
    - *Check:* Gibt es eine "Disk Full" Prevention? Werden alte Logs/Files rotiert oder gelöscht?
    - *Check:* Werden Datenbank-Connections sauber geschlossen (Connection Pooling)?

3.  **Dependency Chains (The Domino Effect):**
    - Analysiere `podman-compose.yml` und Service-Starts.
    - *Check:* Wenn der `controller` hängt, sterben dann auch unabhängige Services (z.B. `livesound`)?
    - *Check:* Sind Timeouts für Netzwerk-Calls (HTTP/DB) gesetzt, oder kann ein Request ewig hängen?

4.  **Error States & Monitoring:**
    - *Check:* Werden kritische Fehler nur geloggt (`print`), oder ändern sie den Health-Status, damit der `healthchecker`/`controller` reagieren kann?

## OUTPUT FORMAT
Erstelle einen **"Resiliency Report"**:

*   **TOP 3 "Death Scenarios":** Die wahrscheinlichsten Gründe, warum das System nach 30 Tagen im Wald stirbt.
*   **Fixing Plan:** Konkrete Maßnahmen (z.B. "Add Timeout to Requests", "Implement Circuit Breaker").

Sprache: Deutsch. Sei gnadenlos ehrlich.
