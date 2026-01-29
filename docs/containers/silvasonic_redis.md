
# Container Spec: silvasonic_redis

> **Rolle:** Echtzeit-Kommunikation, Caching und Message Broker.
> **Tier:** Tier 0 (Vital) – Notwendig für Live-Status und Inter-Container-Kommunikation.

## 1. Executive Summary
* **Problem:** Services müssen lose gekoppelt Nachrichten austauschen (Pub/Sub) und flüchtigen Status (Heartbeats, VU-Meter) teilen, ohne die DB zu hämmern.
* **Lösung:** Redis als in-memory Data Structure Store für High-Speed Operations.

## 2. Technische Spezifikation (Docker/Podman)
Diese Werte sind verbindlich für die Implementierung.

| Parameter | Wert | Begründung/Details |
| :--- | :--- | :--- |
| **Base Image** | `redis:alpine` | Minimales, stabiles Image. |
| **Security Context** | `Rootless (User: pi)` | Standard. |
| **Restart Policy** | `always` | Infrastruktur. |
| **Ports** | `6379:6379` | Intern wichtig. |
| **Volumes** | - `redis_data:/data` | Persistenz (RDB/AOF) optional, aber empfohlen für Restart-Safety. |
| **Dependencies** | `None` | Basis-Service. |

## 3. Interfaces & Datenfluss
* **Inputs (Trigger):**
    *   *SET/PUBLISH:* Heartbeats (alle Container), VU-Meter (Recorder), Alerts (Processor/Birdnet).
* **Outputs (Actions):**
    *   *GET/SUBSCRIBE:* Dashboard (Live-View), Monitor (Alerting).

## 4. Konfiguration (Environment Variables)
*   Standard Redis Config. Ggf. Passwortschutz `REDIS_PASSWORD`.

## 5. Abgrenzung (Out of Scope)
*   KEIN Langzeit-Speicher (Dafür ist TimescaleDB da).

## 6. Architecture & Code Best Practices
*   **Keyspace Notification:** Aktivieren für reactive Patterns (optional).
*   **Healthcheck:** `redis-cli ping`

## 7. Kritische Analyse
*   **Risiko:** Wenn Redis vollläuft (Memory), crasht das System. -> Eviction Policy setzen (`allkeys-lru` oder `volatile-lru`).
