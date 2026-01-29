

# Container Spec: silvasonic_uploader

> **Rolle:** Cloud-Synchronisation und Archivierung.
> **Tier:** Tier 2 (Mission) – Datensicherung.

## 1. Executive Summary
* **Problem:** Lokaler NVMe Speicher ist begrenzt. Wichtige Daten (Tier-Stimmen, Bats) sollen langfristig gesichert werden.
* **Lösung:** Rclone-basierter Uploader, der High-Res Files komprimiert (FLAC) und in die Cloud schiebt.

## 2. Technische Spezifikation (Docker/Podman)
Diese Werte sind verbindlich für die Implementierung.

| Parameter | Wert | Begründung/Details |
| :--- | :--- | :--- |
| **Base Image** | `python:3.11` + `rclone` installiert | Python Wrapper um Rclone CLI. |
| **Security Context** | `Rootless` | Standard. |
| **Restart Policy** | `on-failure` | Background Job. |
| **Ports** | `None` | Outbound only. |
| **Volumes** | - `/data/recordings:/data/recordings` | Read (WAV) / Write (Temp FLAC).<br>- `./config/rclone.conf:/root/.config/rclone/rclone.conf:ro` | Rclone Config. |
| **Dependencies** | `silvasonic_database` | Job Queue. |

## 3. Interfaces & Datenfluss
*   **Trigger:** DB Query `WHERE uploaded=FALSE`.
*   **Action:**
    *   WAV -> FLAC (Compression).
    *   Rclone copy -> Target Remote.
    *   Update DB `uploaded=TRUE`.
    *   Delete local FLAC.

## 4. Konfiguration (Environment Variables)
*   `RCLONE_REMOTE`: Name des Remotes (z.B. `s3-archive`).
*   `UPLOAD_STRATEGY`: `ALL` oder `TAGGED_ONLY` (z.B. nur Bats).

## 5. Abgrenzung (Out of Scope)
*   Löscht KEINE Source-Dateien (das macht der Processor/Janitor basierend auf `uploaded`-Flag).

## 6. Architecture & Code Best Practices
*   **Subprocess:** Aufruf von `rclone` via `subprocess.run`.
*   **Nice:** Prozess mit niedriger Priorität (`nice -n 19`) starten.

## 7. Kritische Analyse
*   **Bandbreite:** Kann Internet verstopfen. Ggf. Bandwidth Limit in Rclone setzen.
