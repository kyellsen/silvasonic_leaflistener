# Container: Dashboard

## 1. Das Problem / Die Lücke
Ein Headless-System (ohne Monitor/Tastatur) im Feld ist schwer zu überwachen. Man weiß nicht, ob es aufnimmt, wie voll die Festplatte ist oder was gerade erkannt wurde. Es fehlte eine benutzerfreundliche Schnittstelle für den lokalen Zugriff (via Hotspot/LAN) zur Visualisierung der Daten und Systemzustände ohne Cloud-Abhängigkeit.

## 2. Nutzen für den User
*   **Sofortiges Feedback:** Sehen, was das Gerät *jetzt gerade* hört und tut.
*   **Daten-Exploration:** Durchsuchen der lokalen Vogel-Detektionen (Listen, Grafiken) direkt am Gerät.
*   **System-Health:** Überprüfung von Speicherplatz, CPU-Last und Service-Status auf einen Blick.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   Datenbank (PostgreSQL) für Detektionen und Statistiken.
    *   Dateisystem (für Zugriff auf Audio-Snippets/Spektrogramme).
    *   System-Metriken (via `psutil` oder Healthchecker-Logs).
*   **Processing:**
    *   Webserver (Uvicorn/FastAPI) zur Bereitstellung der UI.
    *   Aggregation von Statistiken (z.B. "Top 5 Vögel heute").
    *   Rendering von HTML-Templates (Jinja2) und API-Endpoints.
*   **Outputs:**
    *   Web-Interface (HTTP auf Port 80/8080).
    *   Interaktive Grafiken und Audio-Player im Browser.

## 4. Abgrenzung (Out of Scope)
*   Macht **KEINE** Audio-Analyse (Aufgabe von `birdnet` oder `livesound`).
*   Steuert **NICHT** die Hardware (Aufgabe von `controller`).
*   Ist **NICHT** das Internet-Backend (das ist die Cloud/Nextcloud).
*   Das Dashboard ist eine reine *View*-Komponente für lokale Daten.
