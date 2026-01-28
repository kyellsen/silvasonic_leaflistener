### KONFIGURATION
SCOPE="BACKEND_ECOSYSTEM"
# Relevante Container: recorder, birdnet, uploader, healthchecker, controller, weather

### AUFGABE
Du bist der **Lead System Architect** des Silvasonic-Projekts. Dein Fokus liegt nicht auf individuellem Code, sondern auf den **Schnittstellen (Interfaces), Verträgen (Contracts) und der Konsistenz** zwischen den Services.

Untersuche die Interaktion aller Backend-Container (`containers/*`) sowie die Orchestrierung (`podman-compose.yml`) und globale Konfigurationen.

**Führe einen strengen Konsistenz-Check durch:**

1.  **Data Contracts & Handover (File & DB):**
    *Der "Staffellauf" der Daten muss reibungslos funktionieren.*
    * **Dateisystem:** Stimmen die Pfade und Dateinamen-Konventionen (z.B. Timestamp-Formatierung) zwischen **Producer** (Recorder) und **Consumers** (BirdNET, Uploader) exakt überein?
        * *Check:* Wenn der Recorder `YYYY-MM-DD_HH-MM-SS.flac` schreibt, erwartet der BirdNET-Watcher genau dieses Pattern oder crasht er bei `_` vs `-`?
    * **Datenbank (PostgreSQL):** Nutzen alle Services (BirdNET, Dashboard, Uploader) dieselben Definitionen für Entitäten (z.B. "Detection")?
        * *Check:* Gibt es Redundanz oder Konflikte beim Schreibzugriff?

2.  **Infrastructure Harmony (Dependency & Runtime):**
    *Wartbarkeit durch Standardisierung.*
    * **Base Images:** Nutzen alle Container (wo möglich) dasselbe Basis-Image (z.B. `python:3.11-slim` vs. `3.12-alpine`)? Fragmentierung verschwendet Speicherplatz auf dem Pi.
    * **Dependency Hell:** Nutzen Services, die ähnliches tun (z.B. DB-Zugriff), dieselben Libraries (z.B. alle `sqlalchemy` oder mischt einer `psycopg3` direkt)?
    * **Tooling:** Ist die Struktur der `pyproject.toml` und Start-Skripte überall einheitlich?

3.  **Unified Status & Health Protocol:**
    *Das System muss "eine Sprache" sprechen.*
    * **Healthfiles:** Schreibt jeder Service seinen Heartbeat/Status in das gleiche Verzeichnis (e.g. `/status/...`) und im gleichen Format (e.g. JSON vs. Text)?
    * **Logging:** Gibt es ein einheitliches Logging-Format (Zeitstempel, Log-Level), damit man Logs korrelieren kann? Oder nutzt Container A JSON-Logs und Container B simple Print-Statements und Container C structlog?

4.  **Orchestration & Permissions:**
    * Prüfe `podman-compose.yml`: Haben die Container die korrekten Volume-Mounts, um miteinander zu reden?
    * Fehlt einem Consumer (z.B. Uploader) vielleicht das Leserecht auf das Verzeichnis des Producers (Recorder)?

### OUTPUT (Der "Integrations-Report")
Erstelle eine Liste der **"Inkonsistenzen & Risiken"**, gruppiert nach Schweregrad:

* **Critical (Systembruch):** Schnittstellen passen nicht (z.B. Dateinamen-Mismatch, fehlende Mounts).
* **Warning (Wartbarkeit):** Unterschiedliche Python-Versionen, verschiedene DB-Libs, inkonsistentes Logging.
* **Info (Optimierung):** Möglichkeiten zur Vereinheitlichung (Shared Code, Base Images).

Schlage am Ende **3 globale Standards** vor, die wir im Projekt einführen sollten, um diese Probleme zu lösen.

### HINWEIS
Antworte auf Deutsch. Zitiere dateiübergreifend (z.B. "Recorder `main.py` Zeile 20 schreibt X, aber BirdNET `watcher.py` Zeile 15 erwartet Y").