# Container: Recorder

## 1. Das Problem / Die Lücke
Die akustische Überwachung erfordert eine absolut unterbrechungsfreie Aufnahme ("Gapless Architecture"). Wenn Audio-Analyse (CPU-Last) oder Uploads (Netzwerk-Blockaden) im selben Prozess wie die Aufnahme liefe, käme es zwangsläufig zu Datenverlusten ("Dropouts"). Der Recorder existiert als isolierter, privilegierter Container, dessen einzige Aufgabe es ist, Audiodaten sicher vom Kernel auf die SSD zu schreiben.

## 2. Nutzen für den User
*   **Datenintegrität:** Garantiert lückenlose Aufnahmen, auch wenn der Rest des Systems unter Volllast steht (BirdNET rechnet, Uploader hängt).
*   **Hardware-Flexibilität:** Erkennt automatisch verschiedene USB-Mikrofone anhand von Profilen (`mic_profiles`) und wählt die optimalen Einstellungen (Gain, Sample Rate).
*   **Zero-Latency Monitoring:** Stellt einen Live-Stream bereit, damit Nutzer sofort "reinhören" können, ohne auf die abgeschlossene Datei warten zu müssen.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **Audio-Hardware:** Zugriff auf ALSA-Devices (via `/dev/snd`).
    *   **Profile:** Hardware-Definitionen zur Steuerung der FFmpeg-Parameter.
*   **Processing:**
    *   **FFmpeg Wrapper:** Steuert einen persistenten `ffmpeg`-Subprozess zur Aufnahme.
    *   **Segmentierung:** Schneidet den Stream in handliche 10-Sekunden-Chunks (`.flac`).
    *   **Self-Healing:** Überwacht den Aufnahme-Prozess und startet ihn bei Absturz sofort neu.
*   **Outputs:**
    *   **Dateien:** Schreibt `.flac` Dateien (komprimiert) auf das Daten-Volume.
    *   **UDP Stream:** Sendet rohes Audio (PCM) via UDP an den `livesound` Container.
    *   **Metadaten:** Schreibt detaillierten Status (genutztes Profil, Device-Name) in den Heartbeat.

## 4. Abgrenzung (Out of Scope)
*   Analysiert **KEINE** Audiodaten (Aufgabe von `birdnet`).
*   Lädt **NICHTS** ins Internet hoch (Aufgabe von `uploader`).
*   Initialisiert **NICHT** die Soundkarte auf Treiber-Ebene (macht der Linux Kernel).
