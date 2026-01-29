# Container: Recorder

## 1. Das Problem / Die Lücke
Akustische Überwachung erfordert absolut unterbrechungsfreie Aufnahmen ("Gapless"). Wenn rechenintensive Prozesse (Analyse, Upload) im selben Prozess wie die Aufnahme liefen, käme es zu Datenverlusten ("Dropouts"). Der Recorder ist ein isolierter, priorisierter Container für die reine Datenerfassung.

## 2. Nutzen für den User
*   **Datenintegrität:** Garantiert lückenlose Aufnahmen, auch unter Systemlast.
*   **Hardware-Flexibilität:** Automatische Konfiguration von USB-Mikrofonen durch Profile (`mic_profiles`).
*   **Live-Feed:** Stellt einen latenzarmen Stream für das Live-Reinhören bereit.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **Audio-Hardware:** Exklusiver Zugriff auf ALSA-Devices (via `/dev/snd`).
    *   **Profile:** Hardware-Definitionen (Sample Rate, Gain) zur Steuerung von FFmpeg.
*   **Processing:**
    *   **FFmpeg Wrapper:** Steuert einen persistenten `ffmpeg`-Prozess.
    *   **Segmentierung:** Schneidet Audio in 10-Sekunden-Chunks (`.flac`).
    *   **Stream Copy:** Dupliziert den Audio-Stream für UDP-Versand ohne Transcoding.
*   **Outputs:**
    *   **Dateien:** Schreibt `.flac` Dateien auf das Daten-Volume.
    *   **UDP Stream:** Sendet rohes Audio an den `livesound` Container.
    *   **Status:** Schreibt Heartbeat und Metadaten nach Redis (`status:recorder:<id>`).

## 4. Abgrenzung (Out of Scope)
*   Analysiert **KEINE** Audiodaten (-> `birdnet`).
*   Lädt **NICHTS** hoch (-> `uploader`).
*   Initialisiert **NICHT** Treiber (Linux Kernel Aufgabe).
