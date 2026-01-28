# Container: Controller

## 1. Das Problem / Die Lücke
In einer dynamischen Hardware-Umgebung (USB-Mikrofone können ausfallen, ausgesteckt oder neu verbunden werden) ist eine statische Container-Konfiguration ("docker-compose up") unzureichend. Wenn ein Mikrofon disconnected, stürzt ein klassischer Recorder-Container ab und startet in einem Crash-Loop neu. Der Controller füllt diese Lücke durch eine intelligente, **asynchrone Überwachung** ("Supervisor-Pattern"), die Hardware-Events in Echtzeit verarbeitet, ohne blockiert zu werden.

## 2. Nutzen für den User
*   **Plug & Play:** Mikrofone können im laufenden Betrieb getauscht werden; das System erkennt sie sofort und startet die Aufnahme neu.
*   **Höchste Responsive:** Dank **AsyncIO** reagiert das System auch unter Last innerhalb von Millisekunden auf Hardware-Änderungen.
*   **Fehler-Resilienz:** Fehlerhafte Konfigurationen (z.B. falsche YAML-Profile) werden durch **strikte Validierung (Pydantic)** abgefangen, bevor sie Container-Crashes verursachen.
*   **Observability:** Durchgängiges **JSON-Structured Logging (structlog)** ermöglicht maschinenlesbare Logs und einfacheres Debugging.
*   **Ressourcenschonend:** Der Controller verbraucht im Idle-Modus praktisch keine CPU-Zeit durch effizientes Event-Polling statt Busy-Waiting.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   System-Events via `udev` (Non-blocking Monitor mittels `pyudev`).
    *   Hardware-Scan via `arecord -l` (Asynchrone Subprozesse).
    *   Mikrofon-Profile (YAML) -> Validiert durch **Pydantic**.
*   **Processing:**
    *   **Async Event Loop:** Führt I/O-Operationen (Scanning, Podman-Calls) nicht-blockierend aus.
    *   **Reconciliation:** Gleicht Hardware-IST (gefundene Soundkarten) mit Container-SOLL (laufende Recorder) ab.
    *   **Orchestration:** Steuert `recorder` Container via **Podman CLI** Subprozesse (robustes Spawning/Stopping).
    *   **Structured Logging:** Erzeugt Log-Events im JSON-Format via `structlog`.
*   **Outputs:**
    *   Lebenszyklus-Management der Recorder-Container (`spawn`/`stop` mit korrekten Volume-Mounts für `/proc/asound`, `/sys`, etc.).
    *   Live-Konfiguration (`livesound_sources.json`) für das Streaming (Port-Mapping).
    *   System-Heartbeat (`controller.json`) inkl. Vital-Metriken (CPU, RAM) und aktiver Session-Liste.

## 4. Abgrenzung (Out of Scope)
*   Nimmt **KEIN** Audio auf (Aufgabe des Recorders).
*   Analysiert **KEINE** Audiodaten (Aufgabe von BirdNET).
*   Speichert **KEINE** Recordings (Aufgabe des Recorders).
