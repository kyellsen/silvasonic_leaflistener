# Container: Database

## 1. Das Problem / Die Lücke
Ein dateibasiertes System skaliert nicht für Suchanfragen (z.B. "Alle Fledermäuse der letzten Woche"). Es wird ein zentraler, hochperformanter Index benötigt, der Meta-Daten (Aufnahmen, Wetter, KI-Ergebnisse) relational verknüpft und effizient speichert.

## 2. Nutzen für den User
*   **Schnelle Suche:** Sofortiges Filtern von Tausenden Aufnahmen im Dashboard.
*   **Langzeit-Daten:** Speicherung von Wetter- und Aktivitätsdaten über Jahre dank TimescaleDB-Komprimierung.
*   **Zentrale Wahrheit:** Alle Dienste (BirdNET, Dashboard, Uploader) synchronisieren sich über diesen Status.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs**:
    *   **Processor:** Schreibt neue Aufnahmen (`recordings`).
    *   **BirdNET:** Schreibt Erkennungen (`detections`).
    *   **Weather:** Schreibt Wetterdaten (`measurements`).
    *   **Controller/Dashboard:** Lesen/Schreiben Konfiguration (`service_state`).
*   **Processing**:
    *   **Speicherung:** Verwaltet relationale Daten (PostgreSQL 16) und Zeitreihen (TimescaleDB Hypertables).
    *   **Aufräumen (Lifecycle):** Automatische Retention-Policies löschen alte Messwerte (z.B. nach 1 Jahr).
    *   **Integrität:** Stellt sicher, dass Erkennungen gelöscht werden, wenn die zugehörige Aufnahme gelöscht wird (`ON DELETE CASCADE`).
*   **Outputs**:
    *   Bereitstellung von Daten via Port 5432 für alle Container.

## 4. Abgrenzung (Out of Scope)
*   **Keine Dateien:** Speichert NICHT die Audiodateien selbst (nur Pfade/Metadaten).
*   **Kein Backup:** Führt selbstständig keine Cloud-Backups durch (Aufgabe des Users/Uploaders).
