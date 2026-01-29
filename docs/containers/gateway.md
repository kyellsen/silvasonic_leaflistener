# Container: Gateway

## 1. Das Problem / Die Lücke
Wir haben diverse Web-Dienste (Dashboard, Icecast, Upload-Status), die alle auf verschiedenen Ports laufen. Der User möchte aber nur EINE Adresse aufrufen (Port 80/443), sich nur EINMAL authentifizieren und automatisches HTTPS haben.

## 2. Nutzen für den User
*   **Einfachheit:** Zugriff auf das gesamte System über `http://silvasonic.local` (oder gesetzte IP).
*   **Sicherheit:** Kann HTTPS Zertifikate automatisch verwalten (Caddy Feature).
*   **Routing:** Trennt saubere URLs (`/stream` für Audio, `/` für UI).

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs**:
    *   **Eingehender Traffic**: HTTP/HTTPS Anfragen auf Port 80/443.
*   **Processing**:
    *   **Reverse Proxy**: Leitet Anfragen basierend auf Pfad weiter.
*   **Outputs**:
    *   **Routing**:
        *   `/stream*` -> `silvasonic_livesound:8000` (Icecast).
        *   `/*` -> `silvasonic_dashboard:8000` (UI).

## 4. Abgrenzung (Out of Scope)
*   **Keine Logik:** Führt keinerlei Business-Logik aus.
*   **Keine Datenbank:** Speichert nichts.
