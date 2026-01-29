# Container: Recorder

## 1. Das Problem / Die Lücke
Hochwertige Fledermaus-Aufnahmen (384kHz) sind riesig und für das Web (48kHz) unbrauchbar. Gleichzeitig darf die Aufnahme **niemals** abbrechen, nur weil eine Analyse Zeit kostet. Der Recorder ist daher isoliert und macht nur eines: Daten schreiben.

## 2. Nutzen für den User
*   **Stabilität:** Eigene "Prozess-Festung". Wenn BirdNET abstürzt, läuft die Aufnahme weiter.
*   **Performance:** Nutzt `ffmpeg` mit C-Performance für effizientes Splitting der Audio-Streams.
*   **Dual-Stream:** Erzeugt automatisch eine "leichte" Version (48kHz) für das Dashboard und eine "volle" Version (384kHz) für die Wissenschaft/Archiv.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs**:
    *   **USB-Audio:** Liest Rohdaten direkt vom ALSA-Device (exklusiver Zugriff).
    *   **Profile**: Lädt Konfiguration (Sample-Rate, Gain) basierend auf dem erkannten Gerät.
*   **Processing**:
    *   **FFmpeg Split**: Teilt den Audio-Strom in drei Wege:
        1.  **High-Res**: 384kHz WAV (Archiv/Fledermäuse).
        2.  **Low-Res**: 48kHz WAV (Web/Vögel).
        3.  **Live-Stream**: 48kHz MP3 (Icecast/Live-Hören).
*   **Outputs**:
    *   **Dateien**: Schreibt segmentierte `.wav` Dateien nach `/data/recordings/{id}/{high_res|low_res}`.
    *   **Stream**: Sendet MP3-Stream an den `livesound` Container.
    *   **Status**: Meldet Herzschlag (`status:recorder:{id}`) an Redis.

## 4. Abgrenzung (Out of Scope)
*   **Keine Analyse:** Wertet Audio nicht aus.
*   **Kein Upload:** Lädt nichts hoch.
*   **Kein Datenbank-Schreibzugriff:** Schreibt keine Metadaten in die DB (das macht der Processor/Indexer).
