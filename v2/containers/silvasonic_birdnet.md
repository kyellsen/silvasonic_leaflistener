
# Container Spec: silvasonic_birdnet

> **Rolle:** Audio-Analyse Worker (Species Classification).
> **Tier:** Tier 4 (Extras) – Darf jederzeit sterben oder throttled werden.

## 1. Executive Summary
* **Problem:** Wir wollen wissen, welche Vögel/Tiere zu hören sind.
* **Lösung:** Führt BirdNET-Analyzer auf den 48kHz Files aus (Low Res), die der Recorder erstellt hat.

## 2. Technische Spezifikation (Docker/Podman)
Diese Werte sind verbindlich für die Implementierung.

| Parameter | Wert | Begründung/Details |
| :--- | :--- | :--- |
| **Base Image** | `birdnet-analyzer` (Official/Custom) | Tensorflow Lite Runtime. |
| **Security Context** | `Rootless` | Standard. |
| **Restart Policy** | `on-failure` | Tier 4. |
| **Ports** | `None` | Worker. |
| **Volumes** | - `/data/recordings:/data/recordings:ro` | Read-Access. |
| **Dependencies** | `silvasonic_database` | Holt Jobs aus DB. |

## 3. Interfaces & Datenfluss
*   **Trigger:** Polling DB `SELECT * FROM recordings WHERE analyzed_bird=FALSE`.
*   **Action:**
    *   Analysiert Audio.
    *   Schreibt Detections in DB (`measurements` / `detections`).
    *   Updates Recording Status `analyzed_bird=TRUE`.
    *   Publiziert "Bird Detected" Event via Redis.

## 4. Konfiguration (Environment Variables)
*   `CONFIDENCE_THRESHOLD`: 0.7.
*   `LAT/LON`: Für Location Filter.

## 5. Abgrenzung (Out of Scope)
*   Analysiert KEINE Bats (dafür ist BirdNET nicht trainiert - oder nur eingeschränkt).

## 6. Architecture & Code Best Practices
*   **Resource Cap:** Muss via Docker `--cpus` und `--memory` begrenzt werden, um Recorder nicht zu stören.
*   **Batching:** File für File.

## 7. Kritische Analyse
*   **CPU Hog:** ML Inferenz ist teuer. Prio Management ist essenziell (Tier 4).
