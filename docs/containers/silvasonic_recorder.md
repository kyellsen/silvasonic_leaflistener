
# Container Spec: silvasonic_recorder

> **Rolle:** Audio-Akquise und Splitter (High-Res/Low-Res).
> **Tier:** Tier 1 (Core) – Datenintegrität.

## 1. Executive Summary
* **Problem:** Aufnahme von hochfrequentem Audio (384kHz) muss stabil sein ("Record First"). Gleichzeitig werden kleine Files für Web (48kHz) und Live-Streams benötigt.
* **Lösung:** FFMPEG-basierter Container, der direkt vom ALSA-Device liest und den Stream splittet (Tee-Muxer): Stream A (File High), Stream B (File Low), Stream C (Live).

## 2. Technische Spezifikation (Docker/Podman)
Diese Werte sind verbindlich für die Implementierung.

| Parameter | Wert | Begründung/Details |
| :--- | :--- | :--- |
| **Base Image** | `linuxserver/ffmpeg` oder custom Debian mit `ffmpeg` | Braucht aktuelles FFmpeg. |
| **Security Context** | `Rootless` (managed by Controller) | Wird vom Controller mit Device-Passthrough (`--device /dev/snd/...`) gestartet. Läuft als User `1000:1000`. |
| **Restart Policy** | `on-failure` | Managed by Controller. |
| **Ports** | `None` | Streamt outbound zu Icecast. |
| **Volumes** | - `/data/recordings:/data/recordings` | Ziel für WAV Dateien. |
| **Dependencies** | `None` (Standalone Worker). | |

## 3. Interfaces & Datenfluss
* **Inputs (Trigger):**
    *   *Start:* Durch Controller bei USB-Plug.
    *   *Audio:* ALSA Device (`hw:X,Y`).
* **Outputs (Actions):**
    *   *File Write:* 384kHz WAV (Archiv), 48kHz WAV (Analyse).
    *   *Network:* Stream zu `silvasonic_livesound` (Icecast).
    *   *Redis:* Regelmäßige VUmeter Updates (via FFmpeg plugin oder wrapper script).

## 4. Konfiguration (Environment Variables)
*   `AUDIO_DEVICE`: ALSA Device Pfad.
*   `SAMPLE_RATE`: 384000 (oder Profile-Wert).
*   `GAIN`: Lautstärke.
*   `ICECAST_URL`: Optional für Live-Stream.

## 5. Abgrenzung (Out of Scope)
*   Keine Analyse (BirdNET).
*   Keine Metadaten-Verwaltung (Processor).

## 6. Architecture & Code Best Practices
*   **Logic:** Bash Wrapper oder Python Script um `ffmpeg` Process, das Signale (SIGTERM) sauber weiterleitet.
*   **Resilience:** Wenn Icecast weg ist, darf Recording NICHT abbrechen. -> FFmpeg resilient konfigurieren (TCP timeout, non-blocking output für Stream).

## 7. Kritische Analyse
*   **Hardware Access:** Container braucht Zugriff auf `/dev/snd` und `audio` Gruppe.
