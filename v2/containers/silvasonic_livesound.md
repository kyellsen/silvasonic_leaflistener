
# Container Spec: silvasonic_livesound

> **Rolle:** Audio-Streaming Server für Live-Wiedergabe.
> **Tier:** Tier 4 (Extras) – Dispensable bei Last.

## 1. Executive Summary
* **Problem:** Live-Audio von Mikrofonen (Recorders) muss an Web-User gestreamt werden, ohne dass Browser direkt auf Audio-Devices zugreifen können.
* **Lösung:** Icecast Server empfängt Audio-Streams von Recordern und verteilt sie per HTTP an Hörer.

## 2. Technische Spezifikation (Docker/Podman)
Diese Werte sind verbindlich für die Implementierung.

| Parameter | Wert | Begründung/Details |
| :--- | :--- | :--- |
| **Base Image** | `icecast:alpine` | Standard, extrem leichtgewichtig. |
| **Security Context** | `Rootless (User: pi)` | Standard. |
| **Restart Policy** | `on-failure` | Tier 4. Muss nicht zwingend laufen, wenn Ressourcen knapp sind. |
| **Ports** | `8000:8000` | Icecast Standardport. |
| **Volumes** | - `./config/icecast.xml:/etc/icecast.xml:ro` | Konfiguration. |
| **Dependencies** | `None` | Standalone, aber Gateway routet dahin. |

## 3. Interfaces & Datenfluss
*   **Input:** Source Clients (Recorder via `ffmpeg`) connecten und senden MP3/Opus Stream.
*   **Output:** HTTP Audio Stream an Browser (via Gateway `/stream`).

## 4. Konfiguration (Environment Variables)
*   `ICECAST_SOURCE_PASSWORD`: Passwort für Recorder (Source Clients).
*   `ICECAST_ADMIN_PASSWORD`: Admin Panel Zugang.
*   `ICECAST_RELAY_PASSWORD`: (Optional).

## 5. Abgrenzung (Out of Scope)
*   Transcodiert NICHTS (Das macht der Recorder/FFmpeg).
*   Speichert NICHTS.

## 6. Architecture & Code Best Practices
*   **Config:** Minimale `icecast.xml`.
*   **Healthcheck:** TCP Check auf Port 8000.

## 7. Kritische Analyse
*   **Latenz:** Icecast hat systembedingt Latenz (Buffer). Für "Near-Realtime" okay, für Echtzeit-Interaktion Grenzfall.
*   **Alternativen:** WebRTC (Komplexer, Overkill für reines "Reinhören").
