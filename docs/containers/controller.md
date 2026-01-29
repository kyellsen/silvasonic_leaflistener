# Container: Controller

## 1. Das Problem / Die Lücke
Die Hardware-Verwaltung (USB-Mikrofone) und Container-Orchestrierung ist statisch schwer zu lösen (Hot-Plug, dynamische Profile). Der Controller fungiert als "privilegierter Supervisor", der die Brücke zwischen Hardware-Events (udev) und der Container-Welt (Podman) schlägt.

## 2. Nutzen für den User
*   **Plug & Play:** Mikrofone werden beim Einstecken automatisch erkannt und als Container gestartet.
*   **Zentrale Steuerung:** Dienste (z.B. BirdNET) können über das Dashboard (via DB-Config) gestartet/gestoppt werden.
*   **Ausfallsicherheit:** Überwacht den Status von Recordern und startet sie bei Fehlern neu.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs**:
    *   **Hardware-Events**: Überwacht `udev` Events (via `pyudev`) auf USB-Audio-Geräte.
    *   **Konfiguration**: Liest `service_state` Tabelle aus der Datenbank für System-Einstellungen.
    *   **Profile**: Liest Mikrofon-Profile (`*.yml`) aus `/app/mic_profiles`.
*   **Processing**:
    *   **Reconciliation**: Gleicht erkannte Hardware mit laufenden Containern ab (Start/Stop).
    *   **Orchestrierung**: Nutzt den Podman Socket, um `recorder` Container dynamisch zu spawnen (Rootless-kompatibel via User-Mapping).
    *   **Service-Sync**: Startet/Stoppt Applikations-Container (`birdnet`, `uploader`, etc.) basierend auf DB-State.
*   **Outputs**:
    *   **Podman Befehle**: Startet/Stoppt Container.
    *   **Heartbeat**: Sendet `status:controller` Status an Redis (TTL 15s).
    *   **Logs**: Strukturiertes Logging (JSON) nach stdout/File.

## 4. Abgrenzung (Out of Scope)
*   **Kein Audio-Processing:** Berührt niemals Audio-Daten.
*   **Keine Datenbank-Schreibrechte (Daten):** Schreibt keine Aufnahmen oder Detections (nur Config-Lesezugriff).
*   **Kein Root-Dienst:** Läuft zwar im Container privilegiert (für Hardware-Zugriff), spawnt aber Recorder im Kontext des Host-Users (pi).
