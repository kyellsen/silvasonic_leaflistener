# Container: Dashboard

## 1. Das Problem / Die Lücke
Der Benutzer benötigt eine visuelle Schnittstelle, um Aufnahmen zu prüfen, den Systemstatus zu überwachen und Dienste zu konfigurieren, ohne Linux-Experte zu sein oder SSH nutzen zu müssen.

## 2. Nutzen für den User
*   **Zentrale Übersicht:** Zeigt alle Recorder, Speicherplatz und Wetterdaten auf einen Blick.
*   **Bedienbarkeit:** Starten/Stoppen von Diensten (BirdNET, Uploader) per Mausklick.
*   **Analyse:** Visualisierung von Spektrogrammen und Exploration der BirdNET-Ergebnisse mit Filtern.
*   **Datenschutz:** Rollenbasierte Zugriffskontrolle (sofern konfiguriert) und keine Cloud-Abhängigkeit für die UI.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs**:
    *   **User-Requests**: HTTP/HTTPS Anfragen (via Gateway).
    *   **Datenbank**: Liest `recordings`, `detections`, `measurements` und `service_state`.
    *   **Redis**: Zeigt Live-Status der Recorder (`status:recorder:*`) und Systemlast (`status:controller`).
*   **Processing**:
    *   **Rendering**: Server-Side Rendering mit **Jinja2** Templates + **TailwindCSS**.
    *   **Interaktivität**: Nutzung von **HTMX** für dynamische Inhalte ohne Full-Page-Reloads (Polling).
    *   **Auth**: Verwaltet User-Sessions und Sicherheit.
*   **Outputs**:
    *   **HTML/JSON**: Antwortet dem Browser.
    *   **Konfiguration**: Schreibt User-Einstellungen in die `service_state` Tabelle (vom Controller gelesen).

## 4. Abgrenzung (Out of Scope)
*   **Kein Direktzugriff auf Dateien:** Listet niemals Verzeichnisse mit `ls`. Alle Listen kommen aus der Datenbank.
*   **Keine Analyse:** Führt keine KI-Erkennung durch (macht BirdNET).
*   **Kein Audio-Stream:** Streamt Live-Audio nicht selbst (nutzt Icecast/Livesound Container bzw. Link darauf).
