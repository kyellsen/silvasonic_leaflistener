

# Container Spec: silvasonic_weather

> **Rolle:** Umwelt-Daten Logger.
> **Tier:** Tier 4 (Extras).

## 1. Executive Summary
* **Problem:** Bioakustik ist wetterabhängig. Analysen brauchen Kontext (Temperatur, Wind, Regen).
* **Lösung:** Regelmäßiger Fetch von OpenMeteo API (lokale Wetterstation) und Speicherung in DB.

## 2. Technische Spezifikation (Docker/Podman)
Diese Werte sind verbindlich für die Implementierung.

| Parameter | Wert | Begründung/Details |
| :--- | :--- | :--- |
| **Base Image** | `python:3.11-slim-bookworm` | Simple Script. |
| **Security Context** | `Rootless` | Standard. |
| **Restart Policy** | `on-failure` | Low Prio. |
| **Ports** | `None` | Outbound HTTP. |
| **Volumes** | `None` | Stateless. |
| **Dependencies** | `silvasonic_database` | Storage. |

## 3. Interfaces & Datenfluss
*   **Trigger:** Timer (alle 15-20 min).
*   **Source:** HTTP GET OpenMeteo.
*   **Target:** DB Tabelle `weather`.

## 4. Konfiguration (Environment Variables)
*   `LATITUDE`, `LONGITUDE`: Standort.

## 5. Abgrenzung (Out of Scope)
*   Keine eigene Sensor-Hardware-Anbindung (nutzt Web-API).

## 6. Architecture & Code Best Practices
*   **API-Limits:** Beachte Rate Limits von Free APIs.
*   **Resilience:** Wenn Internet weg -> Log & Skip.

## 7. Kritische Analyse
*   Sehr simpler Service, könnte theoretisch Teil des Monitors sein, aber Separation of Concerns (SRP) rechtfertigt eigenen Container.
