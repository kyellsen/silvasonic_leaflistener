# Container: silvasonic_gateway

## 1. Das Problem / Die Lücke
Ohne ein zentrales Gateway müssten Benutzer verschiedene IP-Adressen und Ports (z.B. Dashboard auf 8000, Livesound auf 8001) kennen und Firewall-Regeln für jeden Dienst einzeln konfigurieren. HTTPS-Zertifikate müssten in jedem Dienst separat verwaltet werden.

## 2. Nutzen für den User
*   **Convenience**: Der Nutzer muss nur eine Adresse (z.B. `http://silvasonic.local`) aufrufen.
*   **Sicherheit**: Automatische HTTPS-Verschlüsselung (optional) und zentrale Authentifizierungsmöglichkeiten.
*   **Einheitlichkeit**: Alle Dienste (Dashboard, Audio-Streams) erscheinen als eine kohärente Anwendung.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs**:
    *   Eingehender HTTP/HTTPS Traffic auf Port 80 und 443.
    *   `Caddyfile` Konfiguration (Volume Mount).
*   **Processing**:
    *   Reverse Proxy Routing basierend auf Pfaden.
    *   TLS Termination (HTTPS Management).
    *   Weiterleitung von Requests an interne Container-Hostnames.
*   **Outputs**:
    *   Weitergeleitete HTTP-Requests an `silvasonic_dashboard` und `silvasonic_livesound`.

## 4. Abgrenzung (Out of Scope)
*   **Keine Anwendungslogik**: Führt keinen Python-Code aus.
*   **Kein File-Hosting**: Dient primär als Proxy, nicht als Webserver für statische Dateien (außer evtl. globale Assets).
*   **Keine Datenbank-Kommunikation**: Spricht nicht mit Postgres oder Redis.
*   **Kein Audio-Encoding**: Leitet Audio-Streams nur durch ("blind pipe").

## 5. Technologien die dieser Container nutzt
*   **Basis-Image**: `caddy:alpine`
*   **Wichtige Komponenten**:
    *   Caddy Webserver
    *   Caddyfile (Konfiguration)

## 6. Kritische Punkte
*   **Auth-Verantwortung**: Aktuell unklar, ob das Gateway Basic Auth erzwingen soll oder ob das Dashboard die Authentifizierung übernimmt. Laut Concept V2 wird Basic Auth unterstützt, aber eine doppelte Auth (Gateway + App) kann zu UX-Problemen führen.
*   **WebSocket Support**: Muss korrekt konfiguriert sein, damit Livereviews im Dashboard funktionieren.
