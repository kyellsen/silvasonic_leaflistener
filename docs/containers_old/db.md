# Container: Database (DB)

## 1. Das Problem / Die Lücke
Silvasonic generiert komplexe, strukturierte Daten (Vogel-Detektionen, Wetterdaten, System-Logs, Konfigurationen), die relational verknüpft sind. Flache Dateien (CSV/JSON) skalieren schlecht bei Suchabfragen ("Zeige alle Eichelhäher der letzten Woche"). Ein zentraler, transaktionssicherer Datenspeicher ist für Datenkonsistenz und Performance essenziell.

## 2. Nutzen für den User
*   **Performance:** Das Dashboard kann komplexe Statistiken in Millisekunden abrufen, statt tausende Dateien parsen zu müssen.
*   **Integrität:** Verhindert Datenkorruption bei gleichzeitigen Zugriffen mehrerer Container (BirdNET schreibt, Dashboard liest).
*   **Persistenz:** Daten überleben Container-Neustarts und Updates sicher auf dem Daten-Volume.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **BirdNET:** INSERT von Detektions-Events.
    *   **Weather:** INSERT von Umweltdaten.
    *   **Dashboard:** READ/WRITE von System-Konfigurationen und User-Actions.
    *   **Controller:** Statussynchronisation (via Service-Tabellen).
*   **Processing:**
    *   Bereitstellung einer Standard PostgreSQL-Instanz.
    *   Verwaltung von Indizes (z.B. auf Zeitstempel, Spezies) für schnelle Queries.
*   **Outputs:**
    *   Strukturierte Antwort-Sets (Result Rows) auf SQL-Anfragen.
    *   Persistente Speicherung im Docker-Volume (`pg_data`).

## 4. Abgrenzung (Out of Scope)
*   Enthält **KEINE** Applikationslogik (außer evtl. Stored Procedures / Trigger für Wartungsaufgaben).
*   Speichert **KEINE** großen Blobs (Audio/Bilder bleiben im Filesystem, DB speichert nur Pfade).
