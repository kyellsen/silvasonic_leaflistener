# Container: Dashboard

## 1. Das Problem / Die Lücke
Ein Headless-System im Feld ist ohne Visualisierung eine "Black Box". Der Benutzer benötigt eine intuitive, lokale Schnittstelle (Local-First Ansatz), um das Gerät zu warten, Aufnahmen zu prüfen und Daten zu visualisieren, ohne auf eine Internetverbindung angewiesen zu sein.

## 2. Nutzen für den User
*   **Visuelle Rückmeldung:** Sofortiges Feedback über den Systemstatus und aktuelle Aufnahmen.
*   **System-Kontrolle:** Einfaches Ein-/Ausschalten von Services (z.B. Uploader, Wetter) über eine grafische Oberfläche.
*   **Konfiguration:** Bequeme Verwaltung von Systemeinstellungen (z.B. Upload-Strategie, WLAN) im Browser.
*   **Offline-Fähigkeit:** Volle Funktionalität auch ohne Internetverbindung (z.B. via Hotspot im Wald).

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **Datenbank:** Liest Detektionen, Statistiken und Konfigurationen (`SystemConfig`, `SystemService`) aus PostgreSQL.
    *   **Dateisystem:** Zugriff auf Audio-Dateien und generierte Artefakte (z.B. Spektrogramme).
    *   **Controller-Status:** Liest Status-Dateien des Controllers für Live-Routing Informationen.
    *   **User-Input:** Interaktionen über das Web-Frontend.
*   **Processing:**
    *   **Webserver:** FastAPI Application (via Uvicorn) liefert die Web-Oberfläche aus.
    *   **Rendering:** Generiert dynamische HTML-Seiten (Jinja2 Templates) mit modernem Design (Tailwind CSS).
    *   **Logic Layer:** Aggregiert Statistiken (Caching), verwaltet Authentifizierung und validiert API-Requests.
    *   **Control Plane:** Kommuniziert User-Intents an das System (via DB-State oder API-Calls zum Controller).
*   **Outputs:**
    *   **Web-UI:** Responsives Interface (HTTP) für Browser.
    *   **Status-Updates:** Schreibt Heartbeat und Konfigurationsänderungen in die Datenbank.

## 4. Abgrenzung (Out of Scope)
*   Macht **KEINE** Audio-Analyse (Aufgabe von `birdnet`).
*   Verwaltet **NICHT** die Hardware-Ports oder Container-Lifecycles direkt (Aufgabe von `controller`).
*   Ist **NICHT** die Cloud (fungiert als Edge-Interface, nicht als zentraler Cloud-Server).
