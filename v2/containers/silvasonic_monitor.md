
# Container Spec: silvasonic_monitor

> **Rolle:** System-Watchdog und Notification-Dispatcher.
> **Tier:** Tier 0 (Vital) – Überwachung.

## 1. Executive Summary
* **Problem:** Wenn Services ausfallen oder Events passieren (Fledermaus erkannt), muss der User benachrichtigt werden. Zentrales Alerting verhindert Konfigurations-Chaos.
* **Lösung:** Ein Service überwacht Redis Heartbeats und Channels und leitet Nachrichten via Apprise an externe Dienste (Telegram, Mail, etc.) weiter.

## 2. Technische Spezifikation (Docker/Podman)
Diese Werte sind verbindlich für die Implementierung.

| Parameter | Wert | Begründung/Details |
| :--- | :--- | :--- |
| **Base Image** | `python:3.11-slim-bookworm` | Python Scripting. |
| **Security Context** | `Rootless` | Standard. |
| **Restart Policy** | `always` | Muss Ausfälle anderer melden. |
| **Ports** | `None` | (Evtl. optional interne API, primär aber Redis-Consumer). |
| **Volumes** | - `./config:/app/config:ro` | Secrets (Apprise URLs). |
| **Dependencies** | `silvasonic_redis` | Queue Source. |

## 3. Interfaces & Datenfluss
*   **Input:**
    *   Redis Pub/Sub `alerts`.
    *   Redis Keys `status:*` (Heartbeat Monitoring).
*   **Output:**
    *   Notifications (HTTP Calls zu Telegram/Discord etc.).
    *   Redis `status:system_health`.

## 4. Konfiguration (Environment Variables)
*   `APPRISE_URLS`: Komma-separierte Liste von Services.
*   `CHECK_INTERVAL`: Frequenz für Heartbeat-Checks.

## 5. Abgrenzung (Out of Scope)
*   Generiert KEINE Events (Aggregiert nur).

## 6. Architecture & Code Best Practices
*   **Apprise:** Standard-Library nutzen.
*   **Dead Man's Switch:** Wenn Monitor selbst stirbt -> Kann er nicht melden. (Externe Überwachung nötig, z.B. Healthcheck via Docker).

## 7. Kritische Analyse
*   Single Point of Notification (Gut für Config, Schlecht bei Ausfall).
