

# Container Spec: silvasonic_processor

> **Rolle:** Zentrales "Gehirn" für Datenlogik, Indexierung und Lifecycle-Management (The Brain).
> **Tier:** Tier 1 (Core) – Essenziell für die Datenkonsistenz, Datenverlust bei Ausfall möglich.

## 1. Executive Summary
* **Problem:** Rohdaten (WAVs) landen unstrukturiert auf der Festplatte, ohne dass die Datenbank davon weiß, und müssen verwaltet (gelöscht/archiviert) werden, ohne dass der Recorder blockiert.
* **Lösung:** Ein dedizierter Background-Service scannt das Dateisystem, indexiert Aufnahmen in TimescaleDB, generiert Spektrogramme für die UI und löscht alte Daten basierend auf Speicherplatz-Regeln (Janitor).

## 2. Technische Spezifikation (Docker/Podman)
Diese Werte sind verbindlich für die Implementierung.

| Parameter | Wert | Begründung/Details |
| :--- | :--- | :--- |
| **Base Image** | `python:3.11-slim-bookworm` | Stable Debian Base, erforderlich für `librosa`/`matplotlib` System-Dependencies (z.B. `libsndfile1`). |
| **Security Context** | `Rootless (User: pi)` | Zugriff auf Aufnahmen erforderlich, die dem User `pi` gehören. Keine Hardware-Privilegien nötig. |
| **Restart Policy** | `always` | Tier 1 Service. Muss ständig laufen, um Datenstau zu verhindern. |
| **Ports** | `none` | Kein direkter Netzwerktraffic (API läuft über DB/Redis). |
| **Volumes** | - `/data/recordings:/data/recordings`<br>- `./config:/app/config:ro` | Schreibzugriff auf Recordings für Indexierung und Löschung (Janitor). |
| **Dependencies** | `silvasonic_database`, `silvasonic_redis` | Benötigt DB für Index/State und Redis für Notifications. |

## 3. Interfaces & Datenfluss
* **Inputs (Trigger):**
    * *Filesystem (Polling/Watch):* Scannt `/data/recordings` auf neue `.wav` Dateien (High-Res & Low-Res).
    * *Timer:* Janitor läuft alle 5min.
* **Outputs (Actions):**
    * *Database:* Schreibt Metadaten in Tabelle `recordings` (Path, Timestamp, Duration, Samplerate).
    * *Filesystem (Write):* Erstellt `.png` Spektrogramme neben den High-Res-WAVs (für Bat-Visualisierung).
    * *Filesystem (Delete):* Löscht älteste Dateien wenn Disk > 80% (Warning) oder > 90% (Critical) voll.
    * *Redis:* Publiziert Events auf Channel `alerts` (z.B. "New Bat Detected" oder "Disk Full Warning").

## 4. Konfiguration (Environment Variables)
Liste der Variablen, die der Container zur Laufzeit braucht.

* `DB_URL`: Connection String zur TimescaleDB (z.B. `postgresql://user:pass@silvasonic_database:5432/silvasonic`).
* `REDIS_HOST`: Hostname (Default: `silvasonic_redis`).
* `LOG_LEVEL`: Logging Detail (Default: `INFO`).
* `SCAN_INTERVAL`: Wartezeit zwischen Filesystem-Scans in Sekunden (Default: `10`).
* `DISK_THRESHOLD_WARNING`: Prozentwert für Löschung bereits hochgeladener Dateien (Default: `80`).
* `DISK_THRESHOLD_CRITICAL`: Prozentwert für Not-Löschung (Default: `90`).

## 5. Abgrenzung (Out of Scope)
Was macht dieser Container explizit NICHT?
* Macht KEIN Audio-Recording (Aufgabe von `recorder`).
* Macht KEINE Audio-Analyse/Klassifizierung (Aufgabe von `birdnet` Worker).
* Hat KEINEN Zugriff auf USB/Hardware.
* Bedient KEINE HTTP-Clients (Aufgabe von `dashboard`/`gateway`).

## 6. Architecture & Code Best Practices
* **Libraries:**
    *   `watchdog` (Optional) oder robustes Polling für File-Detection.
    *   `sqlalchemy` + `pydantic` für DB-Interaktion und Validierung.
    *   `librosa` + `matplotlib` für Spektrogramm-Generierung (Thumbnailer).
    *   `redis` für Pub/Sub.
* **Healthcheck:**
    *   Interner Python-Thread aktualisiert Redis Key `status:processor:heartbeat` (TTL 30s).
    *   Docker Healthcheck prüft Existenz/Aktualität dieses Keys via `redis-cli` oder kleines Skript.
* **Fehlerbehandlung:**
    *   "Crash or Retry": Bei DB-Verlust -> Loggen & Retry (Exponential Backoff).
    *   Corrupt Files: Defekte WAVs müssen isoliert/geloggt werden, dürfen den Loop nicht crashen.

## 7. Kritische Analyse
* **Potenzielle Engpässe:**
    *   **Spectrogram Generation:** `librosa` ist CPU-intensiv. Muss in einem separaten Thread/Process laufen oder throttled werden, um IO-Wait nicht zu blockieren.
    *   **Disk IO:** Gleichzeitiges Schreiben (Recorder) und Lesen (Processor/Janitor) auf derselben NVMe. (Sollte kein Problem sein bei NVMe, aber beachten).
* **Alternativen:**
    *   *Inotify (Watchdog):* Theoretisch schneller als Polling, aber auf gemounteten Volumes oder bei High-Write-Load oft unzuverlässig/race-condition-anfällig. **Entscheidung:** Robustes Polling (State-Reconciliation) ist sicherer als reines Event-Listening.
