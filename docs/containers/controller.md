# Container: Controller

## 1. Das Problem / Die Lücke
In einer dynamischen Edge-Umgebung ändern sich Hardware-Zustände (USB-Mikrofone rein/raus) zur Laufzeit. Eine statische Konfiguration via `podman-compose` reicht nicht aus. Das System benötigt eine Instanz, die diese Events überwacht, Container dynamisch steuert ('Supervisor Pattern') und als zentraler Orchestrator für alle Dienste fungiert.

## 2. Nutzen für den User
*   **Plug & Play:** Automatische Erkennung und Einbindung neuer Mikrofone ohne Neustart.
*   **Selbstheilung:** Überwacht Container-Gesundheit und startet ausgefallene Dienste neu (Reconciliation Loop).
*   **Zentrale Steuerung:** Bietet eine API (`Port 8002`) für Dashboard und CLI.
*   **Stabilität:** Verhindert "Restart-Loops" durch intelligente Backoff-Strategien.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **Hardware-Events:** `udev` Signale bei Geräte-Änderungen.
    *   **Container-State:** Status-Abfragen via Podman Socket/CLI.
    *   **Service-Registry:** Konfiguration für System-Services (Wetter, Uploader etc.).
    *   **Profile:** Mikrofon-Profile (`mic_profiles/`) zur Identifikation.
*   **Processing:**
    *   **Reconciliation Loop:** Periodischer Abgleich zwischen SOLL (Profile/Hardware) und IST (laufende Container).
    *   **Orchestration:** Starten/Stoppen von Containern via Podman.
    *   **Monitoring:** Health-Checks und Hardware-Scanning (`arecord -l`).
*   **Outputs:**
    *   **Podman Commands:** Exekutive Befehle an den Container-Daemon.
    *   **API (Port 8002):** HTTP-Endpunkte für Status und Steuerung (FastAPI).
    *   **Legacy Status-Files:** Schreibt JSON-Status nach `/mnt/data/services/silvasonic/status` (z.B. `livesound_sources.json`).
    *   **Persistence:** Speichert Events und State (via PersistenceManager).

## 4. Abgrenzung (Out of Scope)
*   Verarbeitet **KEINE** Audiodaten (-> `recorder`).
*   Analysiert **KEINE** Spektrogramme (-> `birdnet`).
*   Ist **NICHT** die Datenbank (-> `db`).
