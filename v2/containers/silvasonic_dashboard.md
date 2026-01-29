# Container: silvasonic_dashboard

## 1. Das Problem / Die Lücke
Ein komplexes System aus Containern, Datenbanken und Config-Files ist via Command Line (CLI) für Endanwender kaum bedienbar. Es fehlt eine intuitive, grafische Schnittstelle.

## 2. Nutzen für den User
*   **Kontrolle**: Starten/Stoppen von Services, Verwalten von Einstellungen.
*   **Erkundung**: Visuelles Durchsuchen der Aufnahmen (Listen, Filter, Spektrogramme).
*   **Live-Eindruck**: Echtzeit-Ansicht (VU-Meter, Spektrogramm, Status) gibt das Gefühl der Verbundenheit mit der Natur ("Was passiert JETZT?").

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs**:
    *   **HTTP Requests**: Interaktion vom Browser.
    *   **Datenbank**: Lesen von Recordings, Detections, Measurements.
    *   **Redis**: Lesen von Live-Status (`system:status`).
*   **Processing**:
    *   **Server-Side Rendering (SSR)**: Generiert HTML mit Jinja2 Templates.
    *   **API Endpoints**: Stellt JSON für HTMX/Frontend-JS bereit.
    *   **Auth**: Verwaltet User-Sessions (Login/Logout).
*   **Outputs**:
    *   **HTML Interfaces**: Responsive Web-UI.
    *   **Audio**: Streamt/Serviert Audio-Dateien an den Browser.

## 4. Abgrenzung (Out of Scope)
*   **Keine Heavy Calculation**: Berechnet keine Spektrogramme selbst (macht der Processor/Thumbnailer).
*   **Keine System-Verwaltung**: Kann keine Hardware-Treiber installieren oder den Host neustarten (nur Container via Controller-Proxy oder DB-Config).

## 5. Technologien die dieser Container nutzt
*   **Basis-Image**: Python 3.11+
*   **Backend**: `FastAPI` (High Performance Async Web Framework).
*   **Frontend**:
    *   `Jinja2` (Templates).
    *   `TailwindCSS` (Design System für "Premium UI").
    *   `HTMX` (Interaktivität ohne React-Komplexität).
    *   `Alpine.js` (Minimalistisches JS für Client-State).
    *   `Plotly.js` (Graphen).
    *   `Wavesurfer.js` (Audio-Visualisierung).

## 6. Kritische Punkte
*   **Performance vs. Datenmenge**: Das Anzeigen von Listen mit tausenden Aufnahmen muss paginiert sein und DB-Indizes nutzen, sonst wird das Dashboard träge.
*   **Security**: Da es das "Gesicht" nach außen ist, muss es gegen XSS/CSRF gehärtet sein.
*   **Design**: Muss "Best Practice" in UX/UI sein (Dark Mode, Responsive, Polished), um den "Wow"-Faktor zu erfüllen.
