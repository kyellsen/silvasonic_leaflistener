
# Container Spec: silvasonic_database

> **Rolle:** Zentrale Persistenz-Schicht für Metadaten und Status.
> **Tier:** Tier 0 (Vital) – "System Death" bei Ausfall.

## 1. Executive Summary
* **Problem:** Das System benötigt einen performanten Index für Millionen von Audio-Events und Status-Informationen, optimiert für Zeitreihen.
* **Lösung:** TimescaleDB (Postgres-Erweiterung) speichert effizient Zeitreihen (Recordings, Measurements) und dient als State-Backend.

## 2. Technische Spezifikation (Docker/Podman)
Diese Werte sind verbindlich für die Implementierung.

| Parameter | Wert | Begründung/Details |
| :--- | :--- | :--- |
| **Base Image** | `timescale/timescaledb:latest-pg16` | Offizielles Image mit Timescale-Extension. |
| **Security Context** | `Rootless (User: pi)` | Standard Postgres User Mapping. Benötigt Volume-Permissions Fix. |
| **Restart Policy** | `always` | Kern-Infrastruktur. |
| **Ports** | `5432:5432` | Nur intern im Container-Netzwerk nötig (Host-Port optional für Debugging). |
| **Volumes** | - `pg_data:/var/lib/postgresql/data`<br>- `./config/db/init:/docker-entrypoint-initdb.d` | Persistente Daten und Init-Scripte. |
| **Dependencies** | `None` | Basis-Service. |

## 3. Interfaces & Datenfluss
* **Inputs (Trigger):**
    *   *SQL INSERT/UPDATE:* Von `processor` (Recordings), `weather` (Meteo), `birdnet` (Detections).
* **Outputs (Actions):**
    *   *Persistence:* Speichert Daten auf NVMe.
    *   *Query Results:* Liefert Daten an `dashboard` und `processor`.

## 4. Konfiguration (Environment Variables)
*   `POSTGRES_USER`: `silvasonic`
*   `POSTGRES_PASSWORD`: (Secret)
*   `POSTGRES_DB`: `silvasonic`
*   **Tuning (via cmdline oder conf):**
    *   `synchronous_commit = off`
    *   `shared_buffers = 512MB`
    *   `random_page_cost = 1.1`

## 5. Abgrenzung (Out of Scope)
*   Speichert KEINE BLOBs/Binärdaten (Keine WAVs/Bilder in der DB!).
*   Macht KEINE Business-Logik (Keine Stored Procedures für komplexe Abläufe).

## 6. Architecture & Code Best Practices
*   **Hypertables:** Nutze `create_hypertable()` für `recordings` und `measurements`.
*   **Healthcheck:** `pg_isready -U silvasonic`

## 7. Kritische Analyse
*   **Engpässe:** Disk I/O bei hoher Schreiblast (Vermeiden durch Batch-Inserts im Processor).
*   **Alternativen:** SQLite (Legacy, verworfen wegen Concurrency-Problemen und fehlender Timeseries-Optimierung).
