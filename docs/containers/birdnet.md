# Container: BirdNET

## 1. Das Problem / Die Lücke
Die Analyse von Audiodaten mittels Deep Learning ist extrem ressourcenintensiv (CPU/RAM). Würde dieser Prozess synchron im Aufnahmethread laufen, würde die Aufnahme stocken. Zudem benötigen KI-Modelle oft spezifische, große Dependencies (TensorFlow/TFLite), die man nicht im schlanken Recorder-Container haben möchte. BirdNET kapselt diese komplexen Abhängigkeiten und die schwere Rechenlast in einem eigenen Container.

## 2. Nutzen für den User
*   **Automatische Arterkennung:** Verwandelt "stumme" Aufnahmen in durchsuchbare Daten (Welcher Vogel? Wann?).
*   **Entkopplung:** Die Analyse kann langsamer laufen als Echtzeit (z.B. nachts aufholen), ohne dass die Aufnahme gestört wird.
*   **Skalierbarkeit:** Das Modell kann ausgetauscht oder aktualisiert werden, ohne das gesamte System neu aufzusetzen.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   Neue `.flac` Audio-Dateien (via Shared Volume vom Recorder).
    *   BirdNET-Modell (TFLite) und Label-Dateien.
*   **Processing:**
    *   Filesystem-Monitoring: Überwacht Ordner auf neue Dateien.
    *   Preprocessing: Resampling auf 48kHz (falls nötig) und Segmentierung.
    *   Inferenz: Führt das BirdNET-Modell auf den Audio-Segmenten aus.
    *   Filterung: Wendet Konfidenz-Schwellenwerte an (Minimum Confidence).
*   **Outputs:**
    *   Datenbank-Einträge: Schreibt Detektionen (Spezies, Zeit, Konfidenz) in die PostgreSQL Datenbank.
    *   (Optional) Verschieben/Markieren analysierter Dateien.

## 4. Abgrenzung (Out of Scope)
*   Macht **KEINE** Audio-Aufnahme (Aufgabe von `recorder`).
*   Macht **KEINEN** Upload der Dateien (Aufgabe von `uploader`).
*   Zeigt **KEINE** UI an (Aufgabe von `dashboard`).
*   Hört **NICHT** am Mikrofon.
