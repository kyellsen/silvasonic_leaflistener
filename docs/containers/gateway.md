# Container: Gateway

## 1. Das Problem / Die Lücke
Silvasonic besteht aus mehreren unabhängigen Web-Services (Dashboard, LiveSound, Controller), die auf unterschiedlichen Ports laufen. Der Benutzer möchte sich keine Portnummern merken, sondern das System über eine einheitliche URL erreichen. Zudem fehlt internen Services oft eine SSL-Terminierung oder zentrale Security-Layer.

## 2. Nutzen für den User
*   **Single Entrypoint:** Erreichbarkeit aller Dienste über Port 80 (HTTP) unter einer Adresse (z.B. `http://silvasonic.local/`).
*   **Routing:** Transparente Weiterleitung an die richtigen Container (z.B. `/live` -> LiveSound, `/api` -> Dashboard).
*   **Komfort:** Kein Hantieren mit Port 8080 oder 8000 notwendig.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **HTTP Requests:** Empfängt Anfragen auf Port 80.
    *   **Caddyfile:** Routing-Regeln.
*   **Processing:**
    *   **Reverse Proxy:** Leitet Traffic basierend auf Pfad-Präfixen an interne Container weiter (`silvasonic_dashboard`, `silvasonic_livesound`).
    *   **Load Balancing:** (Potenziell) Verteilung von Last, aktuell aber eher 1:1 Mapping.
*   **Outputs:**
    *   **HTTP Responses:** Liefert Antworten der Backend-Services transparent an den Client zurück.
    *   **Ingress Security:** Dient als einziger "offener" Port im externen Netz (Tailnet/LAN).

## 4. Abgrenzung (Out of Scope)
*   Enthält **KEINE** Business-Logik.
*   Speichert **KEINE** Daten.
*   Analysiert **KEINE** Requests inhaltlich (außer Routing).
