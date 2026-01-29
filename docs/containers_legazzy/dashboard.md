# Container: Dashboard

## 1. Das Problem / Die Lücke
Ein Headless-Edge-Device ist ohne Visualisierung eine "Black Box". Der Benutzer benötigt eine intuitive, lokale Schnittstelle (Local-First), um das Gerät zu warten, Aufnahmen zu prüfen, Daten zu visualisieren und Konfigurationen zu ändern, ohne auf eine Cloud-Verbindung angewiesen zu sein.

## 2. Nutzen für den User
*   **Visuelle Rückmeldung:** Sofortiger Einblick in Systemstatus, Speicherplatz und aktuelle Aufnahmen.
*   **System-Kontrolle:** Ein-/Ausschalten von Services (z.B. Uploader, Wetter) und Reboot-Optionen.
*   **Daten-Exploration:** Analyse und Playback der Audio-Aufnahmen mit Spektrogrammen.
*   **Offline-Fähigkeit:** Volle Funktionalität im lokalen Netzwerk (LAN/Hotspot) auch ohne Internet.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **PostgreSQL:** Detektionen, Statistiken und strukturierte System-Konfigurationen (`SystemConfig`, `SystemService`).
    *   **Redis:** Echtzeit-Status der Recorder (`status:recorder:*`) und System-Events.
    *   **Dateisystem:** Lesezugriff auf Audio-Dateien (`/mnt/data/recordings`) und generierte Artefakte.
    *   **Controller-Status:** (Legacy/Fallback) Liest JSON-Statusdateien für Routing-Informationen.
    *   **User-Input:** Interaktionen über das Web-Frontend (HTTP/WebSocket).
*   **Processing:**
    *   **Webserver:** FastAPI Application (via Uvicorn) liefert die Web-Oberfläche.
    *   **Rendering:** Server-Side Rendering (Jinja2) mit modernem UI-Stack (Tailwind CSS, Plotly).
    *   **Logic Layer:** Aggregation von Recording-Statistiken, Authentifizierung und API-Validierung.
    *   **Control Plane:** Übermittelt User-Intents an das System (via DB-State/API).
*   **Outputs:**
    *   **Web-UI:** Responsives Interface (Port 8080) für Browser.
    *   **Status-Updates:** Schreibt Heartbeat und Konfigurationsänderungen in die Datenbank/Redis.

## 4. Abgrenzung (Out of Scope)
*   Macht **KEINE** Audio-Analyse (-> `birdnet`).
*   Verwaltet **NICHT** die Hardware-Ports (-> `controller`).
*   Ist **NICHT** die Cloud (fungiert als lokales Edge-Management).
