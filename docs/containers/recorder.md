# Container: Recorder

## 1. Das konkrete Problem / Die Lücke
Der **Recorder** löst das Problem der **unterbrechungsfreien Audio-Akquise** in einem Ressourcen-limitierten System.
Da Audio-Analyse (BirdNET) sehr CPU-intensiv ist und Uploads (Netzwerk) blockieren können, darf die Aufnahme niemals mit diesen Prozessen in einem einzigen Skript laufen.
Würde man Aufnahme und Analyse mischen, würde eine hohe CPU-Last bei der Analyse zu "Gaps" (Lücken) in der Aufnahme führen.
Der Recorder existiert daher als isolierter, privilegierter Prozess ("The Sacred Loop"), der **nichts anderes tut** als Audiodaten vom Hardware-Treiber auf die SSD zu schreiben. Er hat die höchste Priorität im System.

## 2. Nutzen für den Silvasonic-User
Für den Anwender garantiert dieser Container:
*   **Lückenlose Überwachung**: Keine Sekunde Audio geht verloren, auch wenn das Internet ausfällt oder die KI-Analyse hinterherhinkt.
*   **Datensicherheit**: Die Primärdaten (.flac) werden sofort persistent auf der NVMe-SSD gespeichert. Selbst bei einem Stromausfall sind nur die letzten Millisekunden gefährdet.
*   **Live-Verfügbarkeit**: Durch den UDP-Stream kann der Nutzer jederzeit "live reinhören" (via Dashboard/Livesound), ohne dass die Aufnahme unterbrochen wird.

## 3. Kernaufgaben (Core Responsibilities)
Der Container arbeitet als **Audio-Pipeline-Manager**.

*   **Inputs (Eingabe):**
    *   Greift den Audio-Stream direkt vom ALSA-Subsystem ab (Hardware-Zugriff auf USB-Mikrofon/Soundkarte).
    *   Alternativ: Liest Testdateien im Mock-Modus via `strategies.py`.
*   **Verarbeitung:**
    *   Startet und überwacht einen **FFmpeg-Prozess** als Child-Process.
    *   Puffert den Audio-Stream im RAM (via Pipe).
    *   Komprimiert Audio on-the-fly nach **FLAC**.
    *   Segmentiert den Stream in exakte 10-Sekunden-Dateien.
*   **Outputs (Ausgabe):**
    *   **Dateisystem**: Schreibt indexierte Dateien (`YYYY-MM-DD_HH-MM-SS.flac`) in den Ordner `/mnt/data/services/silvasonic/recorder/recordings`.
    *   **Netzwerk (Lokal)**: Sendet einen rohen PCM-Stream via UDP an den `livesound`-Container zur Visualisierung/Streaming.
    *   **Status**: Schreibt Heartbeat-JSONs nach `/mnt/data/services/silvasonic/status`, damit der Healthchecker die Funktion prüfen kann.

## 4. Abgrenzung (Was ist NICHT seine Aufgabe)
*   **Keine Analyse**: Der Recorder weiß nicht, *was* er aufnimmt. Ob Vogel, Fledermaus oder Stille – er speichert alles blind. Die Auswertung macht **BirdNET**.
*   **Kein Cloud-Sync**: Der Recorder lädt nichts ins Internet. Das ist exklusive Aufgabe des **Uploaders**.
*   **Kein Playback**: Der Recorder spielt nichts ab. Das machen **Dashboard** oder **Livesound**.
*   **Kein Hardware-Management**: Er initialisiert keine Soundkarten-Treiber (das macht das Host-System/Kernel), er nutzt sie nur.
