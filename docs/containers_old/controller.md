# Container: Controller

## 1. Das Problem / Die Lücke
In einer dynamischen Hardware-Umgebung (Edge Device) können USB-Mikrofone ausfallen, ausgesteckt oder neu verbunden werden. Eine statische Container-Konfiguration (klassisches `docker-compose`) würde hier versagen, da abgesteckte Devices zu Container-Abstürzen führen. Das System benötigt eine Instanz, die Hardware-Events überwacht und Container dynamisch managed ('Supervisor Pattern'). Zudem dient er nun als zentraler Service-Orchestrator für das System.

## 2. Nutzen für den User
*   **Plug & Play:** Mikrofone können im laufenden Betrieb getauscht werden; das System erkennt sie und startet die passenden Recorder-Container automatisch.
*   **Stabilität:** Verhindert Crash-Loops von Containern, wenn Hardware fehlt.
*   **Zentrale Steuerung:** Bietet eine API (`port 8002`) für Statusabfragen und Service-Management.
*   **Live-Streaming:** Verwaltet dynamisch die Port-Zuordnungen für das Live-Hören, sodass das Dashboard immer weiß, wo welcher Stream läuft.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **Hardware-Events:** `udev` Events (via `pyudev`) bei USB-Plug/Unplug.
    *   **System-Scan:** Periodisches Polling via `arecord -l` zur Bestandsaufnahme.
    *   **Profile:** YAML-Definitionen (`mic_profiles/`) für bekannte Mikrofone.
*   **Processing:**
    *   **Reconciliation Loop:** Gleicht Hardware-IST-Zustand mit Container-SOLL-Zustand ab (Startet fehlende Recorder, stoppt verwaiste).
    *   **Podman Orchestration:** Nutzt die Podman-Socket/CLI, um Recorder-Container dynamisch zu spawnen und zu stoppen.
    *   **Service Management:** Startet und überwacht generische System-Services (Silvasonic 2.0 Feature).
    *   **Profil-Reload:** Überwacht Änderungen an Profil-Dateien und lädt diese zur Laufzeit neu.
*   **Outputs:**
    *   **Container-Lifecycle:** `podman run ...` Kommandos für Recorder.
    *   **Status-Dateien:** Schreibt `livesound_sources.json` (Stream-Routing), `active_recorders.json` (Inventar) und Heartbeat-Files.
    *   **API:** Exponiert Endpunkte für Status und Kontrolle.

## 4. Abgrenzung (Out of Scope)
*   Verarbeitet **KEINE** Audio-Signale (macht der `recorder`).
*   Analysiert **KEINE** Vogelschreie (macht `birdnet`).
*   Erstellt **KEINE** Audiodateien auf der Disk (macht `recorder`).
