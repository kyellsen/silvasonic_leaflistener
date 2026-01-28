# Container: Database (DB)

## 1. Das Problem / Die Lücke
Silvasonic generiert komplexe, strukturierte Daten (Vogel-Detektionen, Wetterdaten, System-Logs, Konfigurationen), die relational verknüpft sind. Die Speicherung in flachen Dateien skaliert nicht für komplexe Abfragen und Analysen. Ein zentraler, transaktionssicherer Datenspeicher ist für Datenkonsistenz und Performance unerlässlich.

## 2. Nutzen für den User
*   **Performance:** Ermöglicht schnelle Abfragen und Statistiken auch über große Zeiträume und Datenmengen.
*   **Integrität:** Verhindert Datenkorruption bei gleichzeitigem Schreibzugriff mehrerer Container.
*   **Persistenz:** Sichert alle Metadaten, Konfigurationen und Ergebnisse dauerhaft auf dem Daten-Volume, unabhängig von Container-Neustarts.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **BirdNET:** Speichert Analyse-Ergebnisse (Detektionen).
    *   **Weather:** Speichert gesammelte Umweltdaten.
    *   **Dashboard:** Liest/Schreibt System-Konfigurationen und User-Interaktionen.
    *   **Controller:** Synchronisiert Service-Status und Hardware-Events.
*   **Processing:**
    *   **PostgreSQL Engine:** Bereitstellung einer relationalen Datenbankinstanz.
    *   **Indexierung:** Optimierung von Abfragen durch Indizes (z.B. auf Zeitstempel, Spezies).
    *   **Wartung:** Ausführung von Initialisierungsskripten (`/docker-entrypoint-initdb.d/`) beim ersten Start.
*   **Outputs:**
    *   **Query Results:** Liefert strukturierte Daten auf SQL-Anfragen der anderen Container.
    *   **Persistenter Storage:** Hält den Datenbestand im Volume `pg_data`.

## 4. Abgrenzung (Out of Scope)
*   Enthält **KEINE** Applikationslogik (reiner Datenspeicher).
*   Speichert **KEINE** großen Media-Dateien (Audio/Bilder bleiben im Filesystem, DB speichert nur Dateipfade/Metadaten).
