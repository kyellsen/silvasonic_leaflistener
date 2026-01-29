# Container: silvasonic_controller

## 1. Das Problem / Die Lücke
Docker-Container sind normalerweise statisch. USB-Mikrofone werden jedoch dynamisch an- und abgesteckt. Ein statischer Container kann Hardware-Änderungen zur Laufzeit oft nicht sauber abbilden ("Hot-Plug"). Außerdem benötigt der Zugriff auf USB-Hardware privilegierte Rechte, die wir nicht *jedem* Container geben wollen.

## 2. Nutzen für den User
*   **Plug & Play**: USB-Mikrofone werden beim Einstecken automatisch erkannt und starten eine Aufnahme.
*   **Sicherheit**: Nur der Controller läuft privilegiert ("root"), die Recorder-Instanzen können (theoretisch) isolierter laufen bzw. übernehmen User-Rechte via Group-Add.
*   **Resilienz**: Wenn ein Mikrofon ausfällt oder der Recorder crasht, startet der Controller ihn neu, ohne das Gesamtsystem zu stoppen.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs**:
    *   **UDEV Events**: Überwachung des `/devi/bus/usb` auf Hardware-Änderungen.
    *   **Mic Profiles**: Konfigurationsdateien (`.yml`), die definieren, wie mit einem spezifischen Gerät umzugehen ist (Sample Rate, Channels).
*   **Processing**:
    *   **Device Matching**: Vergleicht USB Vendor/Product IDs mit Profilen.
    *   **Orchestration**: Startet und Stoppt dynamisch `silvasonic_recorder_[id]` Container via Podman Socket.
    *   **Service Supervision**: Überwacht den Status der App-Container (optional).
*   **Outputs**:
    *   **Podman Befehle**: `run`, `stop`, `rm` via Unix Socket.
    *   **Redis Heartbeat**: Meldet den eigenen Status und aktive Sessions.

## 4. Abgrenzung (Out of Scope)
*   **Kein Recording**: Der Controller fasst niemals Audio-Daten an.
*   **Kein Indexing**: Er weiß nicht, welche Dateien geschrieben werden.
*   **Kein GUI**: Bietet keine Weboberfläche (außer Status via Redis an das Dashboard).

## 5. Technologien die dieser Container nutzt
*   **Basis-Image**: Python 3.11+
*   **Wichtige Komponenten**:
    *   `podman` (Library oder CLI Wrapper)
    *   `pyudev` (Linux Hardware Events)
    *   `redis` (Status Reporting)
*   **Privilegien**: Benötigt `privileged: true` und Zugriff auf `/run/podman/podman.sock`.

## 6. Kritische Punkte
*   **Single Point of Failure**: Wenn der Controller stirbt, werden keine neuen Mikrofone mehr erkannt (bestehende Aufnahmen laufen aber oft weiter, sofern die Child-Container nicht killt werden).
*   **Podman-in-Docker / Socket-Mount**: Der Zugriff auf den Host-Socket ist mächtig. Der Controller hat effektiv Root-Zugriff auf den Host.
