# Container: silvasonic_database

## 1. Das Problem / Die Lücke
Silvasonic generiert massive Mengen an Metadaten (Recordings, Detections, Logs). Ein einfaches Dateisystem oder SQLite skaliert hierbei nicht für komplexe Zeitreihenabfragen (z.B. "Zeige alle Fledermäuse der letzten 30 Nächte mit >90% Confidence").

## 2. Nutzen für den User
*   **Performance**: Schnelle Suche und Filterung auch bei Millionen von Einträgen.
*   **Datenintegrität**: Sicherstellung, dass Metadaten strukturiert und persistent gespeichert bleiben.
*   **Analyse**: Ermöglicht komplexe Auswertungen (Aktivitätstrends, Artenverteilung).

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs**:
    *   SQL `INSERT/UPDATE` Befehle von `processor`, `birdnet`, `weather`, `uploader`.
    *   SQL `SELECT` Abfragen vom `dashboard`.
*   **Processing**:
    *   Speicherung relationaler Daten (PostgreSQL 16).
    *   Verwaltung von Time-Series Hypertables (TimescaleDB).
    *   Ausführung von Retention Policies (automatisches Löschen alter Messwerte).
*   **Outputs**:
    *   Strukturierte tabellarische Daten (Result Sets).

## 4. Abgrenzung (Out of Scope)
*   **Kein Blob-Storage**: Speichert KEINE Audio-Dateien (WAV/FLAC) oder Bilder (PNG). Nur Pfad-Referenzen.
*   **Keine Business-Logik**: Führt keine Python-Skripte aus; Validierung erfolgt in den Containern.
*   **Kein Public Access**: Wird nicht nach außen (außerhalb des Docker-Netzwerks) exponiert.

## 5. Technologien die dieser Container nutzt
*   **Basis-Image**: `timescale/timescaledb:latest-pg16`
*   **Wichtige Komponenten**:
    *   PostgreSQL 16
    *   TimescaleDB Extension
    *   PostGIS (optional, laut Konzept erwähnt)

## 6. Kritische Punkte
*   **SD-Karte / NVMe**: Bei vielen Schreibzugriffen (Wal-Logs) kann eine SD-Karte schnell verschleißen. Das Konzept empfiehlt NVMe und Tuning (`synchronous_commit = off`).
*   **Schema-Migrationen**: Da wir kein Alembic nutzen (laut `concept.md` "Single Source of Truth is `init.sql`"), sind Schema-Updates bei laufendem Betrieb manuell durchzuführen.
