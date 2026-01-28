# Container: Dashboard

## 1. Das Problem / Die Lücke
Ein Headless-System (ohne Monitor/Tastatur) im Feld ist eine "Black Box". Der Benutzer weiß nicht, ob das System aufnimmt, wie voll der Speicher ist oder was gerade erkannt wurde. Es fehlte eine intuitive, lokale Schnittstelle (Local-First Ansatz), um das Gerät zu warten und Daten zu sichten, ohne auf eine Internetverbindung oder externe Cloud angewiesen zu sein.

## 2. Nutzen für den User
*   **Visuelle Rückmeldung:** Sofortiges Feedback ("Was hört das Gerät jetzt?") und Explorationsmöglichkeiten (Listen, Graphen).
*   **System-Kontrolle:** Services (z.B. Wetter, Uploader) können einfach per Klick ein- oder ausgeschaltet werden.
*   **Konfiguration:** Änderungen an Einstellungen (z.B. Upload-Strategie, WLAN) können bequem über ein Web-Interface vorgenommen werden.
*   **Unabhängigkeit:** Volle Funktionalität auch im Offline-Betrieb (z.B. im Wald via Hotspot).

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **Datenbank:** Liest Detektionen, Statistiken und Konfigurationen (`SystemConfig`, `SystemService`) aus PostgreSQL.
    *   **Filesystem:** Zugriff auf Audio-Dateien und generierte Artefakte (Spektrogramme).
    *   **User-Input:** Interaktionen über das Web-Frontend (Klicks, Formulare).
*   **Processing:**
    *   **Webserver stack:** FastAPI + Uvicorn stellen die Applikation bereit.
    *   **Rendering:** Generiert HTML-Seiten mittels Jinja2-Templates und CSS (Tailwind).
    *   **Logic Layer:** Aggregiert Statistiken (Cache für Performance), verwaltet User-Sessions (Auth) und validiert API-Requests.
    *   **Service Control:** Kommuniziert mit dem Controller (oder via DB-State), um Services zu steuern.
*   **Outputs:**
    *   **Web-UI:** Responsives Interface (HTTP Port 8000/8080/80) für Browser.
    *   **Status-Updates:** Schreibt Heartbeat und ggf. Konfigurationsänderungen zurück in die DB.

## 4. Abgrenzung (Out of Scope)
*   Macht **KEINE** Audio-Analyse (Aufgabe von `birdnet`).
*   Verwaltet **NICHT** die Hardware-Ports oder Container direkt (Aufgabe von `controller`).
*   Ist **NICHT** die Cloud (Nextcloud ist separat).
*   Dient primär als *Visualisierungsschicht* und *Control Plane*.
