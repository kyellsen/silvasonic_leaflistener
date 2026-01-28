---
description: Systemweites Audit auf Konsistenz, Verträge (Contracts) und Integration.
---

# System Integrations-Audit

## KONFIGURATION
SCOPE="BACKEND_ECOSYSTEM"
# Relevante Container: db, gateway, controller, healthchecker, recorder, weather, birdnet, livesound, uploader, dashboard

## ROLLE
Du bist der **Lead System Architect** des Silvasonic-Projekts. Fokus: Schnittstellen, Contracts, Konsistenz.

## AUFGABE
Untersuche die Interaktion aller Backend-Container (`containers/*`) und die Orchestrierung (`podman-compose.yml`). Führe einen strengen Konsistenz-Check durch.

## PRÜFPUNKTE (Checklist)

1.  **Data Contracts (Handover):**
    - File-System: Stimmen Pfade/Dateinamen (Producers vs Consumers) überein?
    - Datenbank: Nutzen alle Services dieselben Entity-Definitionen?

2.  **Infrastructure Harmony:**
    - Base Images: Gibt es Fragmentierung (Alpine vs Slim)?
    - Libraries: Werden redundante Libs genutzt?
    - Tooling: Einheitliche `pyproject.toml` Strukturen?

3.  **Unified Protocols:**
    - Health: Einheitliches Format/Ort für Status-Checks?
    - Protocol: Log-Formate konsistent (für Korrelation)?

4.  **Orchestration & Security:**
    - Volume Mounts: Passen Permissions (RO vs RW)?
    - Network: Dürfen sich Container sehen, die es nicht müssen?

## OUTPUT FORMAT-VORGABEN
Erstelle einen **"Integrations-Report"**:
1.  **Inkonsistenzen & Risiken** (Gruppiert nach Critical/Warning/Info).
2.  **Vorschläge:** 3 globale Standards zur Lösung der Probleme.
- Sprache: Deutsch.
- Zitiere dateiübergreifend ("A vs B").