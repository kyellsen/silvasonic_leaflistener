# Container: Database (DB)

## 1. Das Problem / Die Lücke
Wir haben strukturierte Daten (Vogel-Detektionen, Wetterdaten, System-Logs), die relational verknüpft und effizient durchsuchbar sein müssen. Flat-Files (CSV/JSON) sind für komplexe Abfragen ("Zeige alle Rotkehlchen zwischen 05:00 und 06:00 Uhr mit Konfidenz > 0.8") zu langsam und unhandlich. Es wird ein persistenter, transaktionssicherer Speicher benötigt.

## 2. Nutzen für den User
*   **Historie:** Ermöglicht Langzeitanalysen über Wochen oder Monate.
*   **Schnelligkeit:** Das Dashboard kann Aggregationen (z.B. "Anzahl Detektionen pro Woche") in Millisekunden abrufen, statt tausende Dateien zu parsen.
*   **Datenhoheit:** Alle Metadaten liegen lokal auf dem Gerät und sind auch offline verfügbar.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   `birdnet`: Schreibt neue Detektionen (Species, Confidence, Time).
    *   `weather`: Schreibt Umgebungsdaten.
    *   `recorder`: (Optional) Metadaten zu Aufnahmen.
*   **Processing:**
    *   Speicherung relationaler Daten.
    *   Indizierung für schnelle Suchanfragen.
    *   Ausführung von SQL-Queries durch andere Container.
*   **Outputs:**
    *   Result-Sets für Dashboard-Anfragen.
    *   Persistente Speicherung auf dem Daten-Volume.

## 4. Abgrenzung (Out of Scope)
*   Der Container selbst enthält meist keine eigene Applikationslogik (nur Standard PostgreSQL).
*   Speichert **KEINE** Audio-Blobs (nur Referenzen/Dateipfade auf das Filesystem).
