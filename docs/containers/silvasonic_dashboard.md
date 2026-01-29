
# Container Spec: silvasonic_dashboard

> **Rolle:** User Interface für Visualisierung und Steuerung.
> **Tier:** Tier 3 (UX) – Inconvenience bei Ausfall.

## 1. Executive Summary
* **Problem:** Nutzer brauchen eine intuitive Oberfläche, um Aufnahmen zu durchsuchen, Spektrogramme zu sehen und den Systemstatus zu prüfen.
* **Lösung:** Eine FastAPI Webanwendung, die Daten aus TimescaleDB/Redis liest und modernes UI (HTMX/Tailwind) bereitstellt.

## 2. Technische Spezifikation (Docker/Podman)
Diese Werte sind verbindlich für die Implementierung.

| Parameter | Wert | Begründung/Details |
| :--- | :--- | :--- |
| **Base Image** | `python:3.11-slim-bookworm` | Standard Python Web Stack. |
| **Security Context** | `Rootless (User: pi)` | Reiner Web-Service. |
| **Restart Policy** | `on-failure` | Tier 3. |
| **Ports** | `8000:8000` | Interner Port, exposed via Gateway. |
| **Volumes** | - `/data/recordings:/data/recordings:ro` | Read-Only Zugriff auf Aufnahmen (für Playback/Spectrogram).<br>- `./config:/app/config:ro` | Config. |
| **Dependencies** | `silvasonic_database`, `silvasonic_redis` | Backend Services. |

## 3. Interfaces & Datenfluss
*   **Input:** HTTP Requests (User).
*   **Output:** HTML/JSON.
*   **Reads:** DB (Lists), Redis (Live Status), Filesystem (Audio/Images).

## 4. Konfiguration (Environment Variables)
*   `DB_URL`: Database.
*   `REDIS_HOST`: Redis.

## 5. Abgrenzung (Out of Scope)
*   Liest Files NICHT via `ls` (nutzt DB Index).
*   Löscht KEINE Files (Processor Aufgabe).

## 6. Architecture & Code Best Practices
*   **FastAPI:** Async Support.
*   **Static Files:** Werden vom Gateway oder FastAPI ausgeliefert (Gateway effizienter für `/media`).
*   **Healthcheck:** `curl localhost:8000/health`.

## 7. Kritische Analyse
*   **Performance:** Spectrogram-Rendering (on-demand) kann CPU fressen. -> Caching oder Pre-Generation (Processor) nutzen.
