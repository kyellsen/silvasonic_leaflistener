# Container: Recorder

## 1. Das konkrete Problem / Die Lücke
Der **Recorder** löst das Problem der **unterbrechungsfreien Audio-Akquise** in einem Ressourcen-limitierten System.
Da Audio-Analyse (BirdNET) sehr CPU-intensiv ist und Uploads (Netzwerk) blockieren können, darf die Aufnahme niemals mit diesen Prozessen in einem einzigen Skript laufen.
Würde man Aufnahme und Analyse mischen, würde eine hohe CPU-Last bei der Analyse zu "Gaps" (Lücken) in der Aufnahme führen.
Der Recorder existiert daher als isolierter, privilegierter Prozess ("The Sacred Loop"), der **nichts anderes tut** als Audiodaten vom Hardware-Treiber auf die SSD zu schreiben. Er hat die höchste Priorität im System.

## 2. Nutzen für den Silvasonic-User
Für den Anwender garantiert dieser Container:
*   **Lückenlose Überwachung**: Garantierte Audio-Kontinuität durch Prozess-Isolation, auch wenn BirdNET oder Netzwerk stocken.
*   **Hardware-Flexibilität**: Durch das neue **Profile-System (Pydantic)** werden verschiedene Mikrofone (Rode, Generic USB) automatisch erkannt und mit optimalen gain/sample-rate Einstellungen geladen.
*   **Datensicherheit**: Speichert primäre Audiodaten sofort persistent als FLAC.
*   **Transparenz**: Detaillierte Echtzeit-Statusberichte (JSON) über CPU-Last, Memory und aktives Hardware-Profil.
*   **Live-Streaming**: Zero-Latency UDP-Stream zum `livesound` Container für direktes Reinhören.

## 3. Kernaufgaben (Core Responsibilities)
Der Container arbeitet als **Audio-Pipeline-Manager**.

*   **Inputs (Eingabe):**
    *   **Hardware (ALSA)**: Liest Audio direkt vom Kernel-Subsystem (via `AlsaStrategy`). Nutzt USB-IDs zur strikten Identifikation der Hardware.
    *   **Mock (File Injection)**: Für Development/Testing ohne Hardware – liest Audio-Loops aus Verzeichnissen (via `FileMockStrategy`).
    *   **Konfiguration**: Validiert Hardware-Profile strikt gegen **Pydantic Models** aus `mic_profiles.yml`.

*   **Processing (Verarbeitung):**
    *   **Engine**: Steuert einen persistenten **FFmpeg-Child-Process** (`subprocess`).
    *   **Logging**: Erzeugt strukturierte JSON-Logs via **structlog** für einfache Maschinen-Lesbarkeit (ELK-Stack ready).
    *   **Resilience**: Überwacht den FFmpeg-Prozess und startet ihn bei Absturz automatisch neu ("Self-Healing").
    *   **Build**: Basiert auf modernem Multi-Stage Dockerfile mit **uv** Package Manager für minimale Image-Größe.

*   **Outputs (Ausgabe):**
    *   **Dateisystem**: Schreibt FLAC-Dateien in 10-Sekunden-Chunks.
        *   Pfad: `/mnt/data/services/silvasonic/recorder/recordings/[PROFILE_SLUG]/YYYY-MM-DD_HH-MM-SS.flac`
        *   *(Hinweis: Erstellt jetzt Unterordner basierend auf Recorder-ID oder Profil-Name)*
    *   **UDP Stream**: Sendet 16-bit PCM Raw Audio (Mono) an `livesound` (Port via Config).
    *   **Status**: Schreibt Heartbeat-JSON nach `/mnt/data/services/silvasonic/status/recorder_[ID].json`.
        *   Enthält jetzt Metadaten zum aktiven Mikrofon-Profil und genutzter Hardware.

## 4. Abgrenzung (Was ist NICHT seine Aufgabe)
*   **Keine Analyse**: Der Recorder weiß nicht, *was* er aufnimmt. Ob Vogel, Fledermaus oder Stille – er speichert alles blind. Die Auswertung macht **BirdNET**.
*   **Kein Cloud-Sync**: Der Recorder lädt nichts ins Internet. Das ist exklusive Aufgabe des **Uploaders**.
*   **Kein Playback**: Der Recorder spielt nichts ab. Das machen **Dashboard** oder **Livesound**.
*   **Kein Hardware-Init**: Er verlässt sich darauf, dass das Host-System (Kernel/ALSA) die Soundkarten bereits initialisiert hat.
