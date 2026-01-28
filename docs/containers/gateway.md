# Container: Gateway

## 1. Das Problem / Die Lücke
Silvasonic besteht aus mehreren Web-Services (Dashboard, LiveSound, Controller), die auf unterschiedlichen Ports laufen (z.B. 8080, 8000, 8002). Für den Endanwender ist es umständlich, sich verschiedene Ports zu merken (`http://silvasonic.local:8080`). Zudem fehlt ohne Gateway eine zentrale Stelle für HTTPS-Terminierung oder Authentifizierung.

## 2. Nutzen für den User
*   **Single Entrypoint:** Der Nutzer erreicht alle Dienste über eine einzige Adresse (Port 80), z.B. `http://silvasonic.local/`.
*   **URL-Routing:** Saubere Trennung der Dienste durch Pfade (z.B. `/api` zum Dashboard, `/live` zum LiveSound).
*   **Security:** Ermöglicht zentrales Hardening (z.B. SSL/TLS, Header-Security) an einer Stelle, ohne jeden internen Service anpassen zu müssen.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **HTTP Requests:** Empfängt alle eingehenden HTTP-Anfragen auf Port 80 (und optional 443).
    *   **Caddyfile:** Konfiguration der Routen und Upstreams.
*   **Processing:**
    *   **Reverse Proxy:** Leitet Anfragen basierend auf dem Pfad an den zuständigen internen Container weiter (`dashboard`, `livesound`, `controller`).
    *   **Static Assets:** Dient potenziell als Cache oder Server für statische Dateien (optional).
*   **Outputs:**
    *   **HTTP Responses:** Liefert die Antworten der Backend-Services transparent an den Client zurück.

## 4. Abgrenzung (Out of Scope)
*   Enthält **KEINE** Business-Logik.
*   Speichert **KEINE** Daten.
*   Ist **NICHT** die Firewall (iptables/System-Firewall liegt darunter).
