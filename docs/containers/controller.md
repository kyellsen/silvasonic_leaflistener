# Container: Controller

## 1. Das Problem / Die Lücke
In einer dynamischen Hardware-Umgebung (Edge Device) können USB-Mikrofone ausfallen, ausgesteckt oder neu verbunden werden. Eine statische Container-Konfiguration würde hier versagen. Das System benötigt eine Instanz, die Hardware-Events überwacht und Container dynamisch managed ('Supervisor Pattern'). Zudem dient der Controller als zentraler Service-Orchestrator für das gesamte Silvasonic-Ökosystem (Version 2.0).

## 2. Nutzen für den User
*   **Plug & Play:** Mikrofone können im laufenden Betrieb getauscht werden; das System erkennt sie und startet automatisch die passenden Recorder-Container.
*   **Stabilität:** Verhindert Crash-Loops durch intelligente "Backoff"-Strategien im Reconciliation Loop.
*   **Zentrale Steuerung:** Bietet eine API (`port 8002`) für Statusabfragen und Service-Management (Start/Stop von Plugins).
*   **Live-Streaming Routing:** Verwaltet dynamisch die Port-Zuordnungen für das Live-Hören und stellt diese dem Dashboard bereit.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **Hardware-Events:** `udev` Events (via `pyudev`) bei USB-Plug/Unplug.
    *   **System-Scan:** Periodisches Polling der Audio-Hardware (via `arecord -l`).
    *   **Profile:** YAML-Definitionen (`mic_profiles/`) zur Identifikation und Konfiguration von Mikrofonen.
    *   **Service-Registry:** Definitionen generischer Services (z.B. Wetter, Uploader) aus Konfigurationsdateien.
*   **Processing:**
    *   **Reconciliation Loop:** Gleicht Hardware-IST-Zustand mit Container-SOLL-Zustand ab (Startet fehlende Recorder, stoppt verwaiste).
    *   **Podman Orchestration:** Nutzt die Podman-Socket/CLI, um Container dynamisch zu spawnen und zu stoppen.
    *   **Service Management:** Startet, überwacht und stoppt funktionale System-Services basierend auf der Konfiguration.
    *   **Health Checks:** Überwacht laufende Container und startet sie bei Abstürzen neu (Self-Healing).
*   **Outputs:**
    *   **Container-Lifecycle:** Exekutive Kontrolle über Podman-Container.
    *   **Status-Dateien:** Schreibt `livesound_sources.json` (Stream-Routing) und `active_recorders.json` (Inventar) für andere Services.
    *   **API:** Exponiert REST-Endpunkte auf Port 8002 für das Dashboard.

## 4. Abgrenzung (Out of Scope)
*   Verarbeitet **KEINE** Audio-Signale (macht der `recorder`).
*   Analysiert **KEINE** Audiodaten (macht `birdnet`).
*   Speichert **KEINE** Audiodaten (macht `recorder`).
