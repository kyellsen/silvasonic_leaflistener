# Architecture Audit: Silvasonic System (2026-01-28)

## 1. Strukturtabelle der Services

| Container Service | Criticality Level | Kardinalität | Gesteuert durch | Abhängigkeiten (Depends_on / Needs) |
| :--- | :--- | :--- | :--- | :--- |
| **controller** | **Level 1: System Core** | Singleton | Podman-Compose / Systemd | `db` (Postgres), Docker Socket, Hardware (/dev) |
| **db** | **Level 1: System Core** | Singleton | Podman-Compose | Volume Storage |
| **recorder** | **Level 2: Functional Core** | **Multi-Instance** (1 pro USB-Device) | **Controller** (Dynamic) | USB-Hardware, Profile-Config, Host-Volume Mounts |
| **livesound** | **Level 2: Functional Core** | Singleton | Podman-Compose | UDP Ports (8003+), Shared Volume (Recordings) |
| **dashboard** | **Level 2: Functional Core** | Singleton | Podman-Compose | `db`, Shared Volumes (Status, Profiles), `controller` API |
| **healthchecker** | **Level 2: Functional Core** | Singleton | Podman-Compose | Shared Volumes (Status, Errors), SMTP (Optional) |
| **uploader** | **Level 3: On-Demand** | Singleton | Podman-Compose | `db`, External Internet Connection |
| **birdnet** | **Level 3: On-Demand** | Singleton (aktuell) | **Controller** (ServiceManager) | `recorder` (Output Files), Shared Volumes |
| **weather** | **Level 3: On-Demand** | Singleton (aktuell) | **Controller** (ServiceManager) | Shared Volumes |

---

## 2. Analyse-Ergebnisse & Architekturschwächen

### Phase 1: Service Criticality
Das System hat eine klare Trennung zwischen Infrastruktur (L1) und Anwendung (L2).
*   **Risiko**: Die Datenbank (`db`) ist ein harter Abhängigkeitspfad für `controller` und `uploader`. Wenn die DB hängt, kann der Controller keine Container starten (Start-Reihenfolge in Compose).
*   **Beobachtung**: Der `healthchecker` überwacht zwar, ist aber selbst kein L1-Service ("Watch the Watchmen"-Problem: Wenn er stirbt, gibt es keine Alerts mehr).

### Phase 2: Orchestrierung & Dynamik (The Controller Role)
Der Controller agiert als **hybrider Supervisor**.
*   **Scope**: Er verwaltet nicht nur Hardware-gebundene `recorder`, sondern übernimmt via `ServiceManager` auch die Kontrolle über reine Software-Dienste wie `birdnet`. Das macht ihn zum zentralen "Brain".
*   **Mechanism**: Nutzung der Podman Socket API (`/run/podman/podman.sock`). Er startet Container mit `--replace`, was robust ist.
*   **Recovery-Lücke (Missing Loop)**:
    *   Für `recorder`: Es gibt eine `monitor_hardware` Schleife. Wenn ein Gerät neu erkannt wird, wird der Container gestartet. Aber: Wenn der Container abstürzt (Process Exit), aber das USB-Gerät eingesteckt bleibt, erkennt der Controller dies **nicht sofort**, da er sich auf `udev` Events verlässt. Es fehlt ein `reconcile_loop`, der periodisch prüft "Ist Container X für Device Y noch da?".
    *   Für Generic Services (`birdnet`): Diese werden nur einmal beim Start (`Generic Service Startup`) hochgefahren. Wenn `birdnet` abstürzt, gibt es **keinen Mechanismus**, der ihn neu startet (außer einem kompletten Controller-Neustart).

### Phase 3: Kardinalität & Skalierung
*   **Recorder (Multi-Instance)**: Exzellent gelöst. Nutzung von `card_id` zur Generierung eindeutiger Container-Namen (`silvasonic_recorder_{id}`) und Ports (12000 + ID).
*   **Inkonsistenz**: `uploader` ist fix in `podman-compose.yml`, während `birdnet` und `weather` dynamisch im Controller-Code (`service_manager.py`) definiert sind. Das führt zu einer "Split-Brain"-Konfiguration: Manche optionalen Dienste werden via 'docker up' gestartet, andere via Controller-Logik.

### Phase 4: Konfiguration & Discovery
*   **Push-Modell**: Die Container sind "dumm" und wissen nichts von ihrer Rolle. Der Controller injiziert alles via ENV-Vars (`RECORDER_ID`, `LIVE_STREAM_PORT`). Das ist gut für die Entkopplung.
*   **Health Status (Filesystem-Based)**: Status wird über JSON-Dateien in einem Shared Volume (`/status`) ausgetauscht.
    *   **Vorteil**: Extrem simpel, keine Netzwerk-Overhead, persistente "Last Known State" Info.
    *   **Nachteil**: I/O-Last auf SD-Karten (bei Edge Devices). Race Conditions möglich (File Locking nicht explizit sichtbar).
    *   **Ghosting**: Der `healthchecker` muss explizit "Ghost Files" (Status-Dateien von toten Containern) aufräumen. Das ist fehleranfällig.

### Zusammenfassung der Architektur-Risiken
1.  **Orchestrierungs-Split**: Mischeinsatz von `podman-compose` (statisch) und `controller` (dynamisch) für On-Demand Services erschwert das Verständnis ("Wo ist der Service definiert?").
2.  **Kein "Self-Healing" für dynamische Services**: Der Controller startet `birdnet` nur einmal. Kein Supervisor-Loop.
3.  **Datenbank-Abhängigkeit**: Der Controller (Infrastruktur) hängt von der App-Datenbank ab. Wenn die DB korrupt ist, fährt das System keine Hardware mehr hoch.
4.  **Hardcoded Config**: Die Konfiguration für `birdnet` und `weather` (Image, Mounts) ist fest in `service_manager.py` einkompiliert. Änderungen erfordern ein Controller-Update.
