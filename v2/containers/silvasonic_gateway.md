
# Container Spec: silvasonic_gateway

> **Rolle:** Zentraler Einstiegspunkt (Reverse Proxy) und TLS-Terminierung.
> **Tier:** Tier 0 (Vital) – Ohne Gateway keine Erreichbarkeit.

## 1. Executive Summary
* **Problem:** Mehrere Services (Dashboard, Livesound) müssen über Standardports (80/443) erreichbar sein, ohne Port-Kollisionen.
* **Lösung:** Ein Caddy Server routet Anfragen basierend auf Pfaden an die internen Container und managed automatisch HTTPS (falls konfiguriert).

## 2. Technische Spezifikation (Docker/Podman)
Diese Werte sind verbindlich für die Implementierung.

| Parameter | Wert | Begründung/Details |
| :--- | :--- | :--- |
| **Base Image** | `caddy:alpine` | Offizielles, leichtes Image. Automatische TLS-Verwaltung. |
| **Security Context** | `Rootless (User: pi)` | Möglich durch Host-Sysctl `net.ipv4.ip_unprivileged_port_start=80`. |
| **Restart Policy** | `always` | Infrastruktur-Komponente. Muss immer laufen. |
| **Ports** | `80:80`, `443:443` | HTTP/HTTPS Einstiegspunkte. |
| **Volumes** | - `./config/caddy/Caddyfile:/etc/caddy/Caddyfile`<br>- `caddy_data:/data`<br>- `caddy_config:/config` | Persistenz für Zertifikate und Konfiguration. |
| **Dependencies** | `None` | Startet als erster Service im Network Mesh. |

## 3. Interfaces & Datenfluss
* **Inputs (Trigger):**
    *   *HTTP Request:* Eingehender Traffic von Usern (Browser/API).
* **Outputs (Actions):**
    *   *Reverse Proxy:* Leitet Traffic weiter an:
        *   `silvasonic_dashboard:8000` (Default `/`)
        *   `silvasonic_livesound:8000` (`/stream`)
        *   `silvasonic_docs` (Optional, static files)

## 4. Konfiguration (Environment Variables)
*   `DOMAIN`: Domain für Auto-HTTPS (Optional, Default: `localhost`).
*   `BASIC_AUTH_USER`: Username für Caddy Basic Auth (Falls Dashboard keine Auth hat).
*   `BASIC_AUTH_PASS`: Hash für Caddy Basic Auth.

## 5. Abgrenzung (Out of Scope)
*   Macht KEINE Anwendungslogik.
*   Speichert KEINE Daten (außer SSL Certs).

## 6. Architecture & Code Best Practices
*   **Caddyfile:** Deklarative Config. Keep it simple.
*   **Healthcheck:** `wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1`

## 7. Kritische Analyse
*   **Engpässe:** CPU bei SSL Termination auf Pi Zero (für Pi 5 vernachlässigbar).
