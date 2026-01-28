# Container: Database (DB)

## 1. Das Problem / Die Lücke
Silvasonic generiert komplexe, relational verknüpfte Daten (Vogel-Detektionen, Wetterdaten, Logs, Konfigurationen). Die Speicherung in flachen Dateien skaliert nicht und bietet keine Transaktionssicherheit. Ein zentraler SQL-Datenspeicher ist für Datenkonsistenz, Integrität und performante Abfragen unerlässlich.

## 2. Nutzen für den User
*   **Performance:** Ermöglicht schnelle Filterung und Statistiken über große Zeiträume.
*   **Integrität:** Verhindert Datenkorruption bei gleichzeitigem Zugriff mehrerer Container (ACID-Compliance).
*   **Persistenz:** Sichert alle Metadaten und Ergebnisse dauerhaft auf dem Daten-Volume, unabhängig von Container-Neustarts.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **BirdNET:** Speichert Analyse-Ergebnisse (Detektionen).
    *   **Weather:** Speichert Umweltdaten.
    *   **Dashboard:** Liest/Schreibt System-Konfigurationen.
    *   **Controller:** Synchronisiert Service-Status.
*   **Processing:**
    *   **PostgreSQL Engine:** Bereitstellung einer relationalen Datenbankinstanz.
    *   **Wartung:** Automatische Initialisierung (`init/`) beim ersten Start.
*   **Outputs:**
    *   **Query Results:** Liefert strukturierte Daten auf SQL-Anfragen via Port 5432.
    *   **Persistenter Storage:** Hält den Datenbestand im Volume `pg_data`.

## 4. Abgrenzung (Out of Scope)
*   Enthält **KEINE** Applikationslogik (Business Logic liegt in den Services).
*   Speichert **KEINE** großen Audio-Dateien (Referenziert Dateipfade).
