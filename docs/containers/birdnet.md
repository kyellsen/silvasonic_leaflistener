# Container: BirdNET

## 1. Das Problem / Die Lücke
Die Analyse von Audiodaten mittels Deep Learning ist extrem ressourcenintensiv (CPU/RAM). Eine synchrone Ausführung im Aufnahmethread (Recorder) würde zu Audio-Dropouts ("Knacksern") oder Überlastung führen. Zudem benötigen KI-Modelle oft schwere Abhängigkeiten (TensorFlow Lite, Librosa), die vom schlanken, stabilen Recorder-Container isoliert werden müssen ("Dependency Hell" vermeiden).

## 2. Nutzen für den User
*   **Automatische Arterkennung:** Verwandelt "stumme" .flac-Dateien in durchsuchbare Metadaten (Spezies, Zeitstempel, Konfidenz).
*   **Asynchrone Verarbeitung:** Die Analyse läuft entkoppelt (z.B. tagsüber aufnehmen, nachts "aufholen"), ohne die kritische Audio-Aufnahme zu gefährden.
*   **Modularität:** Das Erkennungsmodell und die Analyselogik können aktualisiert werden, ohne das Aufnahmesystem zu berühren.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **Audio-Dateien:** `.flac` Dateien via Shared Volume (vom Recorder).
    *   **Konfiguration:** `config.yml` (Schwellenwerte, Geo-Location, Filter).
    *   **Modell:** BirdNET TFLite Modell und Label-Dateien.
*   **Processing:**
    *   **Watcher:** Überwacht Verzeichnisse rekursiv auf neue Dateien (via `watchdog`).
    *   **Preprocessing:** Resampling, Segmentierung und Normalisierung der Audiodaten.
    *   **Inferenz:** Ausführung des Neural Networks (BirdNET-Analyzer).
    *   **Filtering:** Anwendung von Konfidenz-Schwellenwerten und Geo-Filtern.
*   **Outputs:**
    *   **Datenbank:** Schreibt Ergebnisse (Detections) via SQLAlchemy/Psycopg2 in die PostgreSQL DB.
    *   **Logs:** Strukturiertes Logging des Analysefortschritts.
    *   **Redis:** (Potenziell) Status-Reporting oder Caching (gemäß Abhängigkeiten).

## 4. Abgrenzung (Out of Scope)
*   Macht **KEINE** Audio-Aufnahme (Aufgabe von `recorder`).
*   Macht **KEINEN** Upload (Aufgabe von `uploader`).
*   Bietet **KEINE** GUI (Aufgabe von `dashboard`).
*   Greift **NICHT** auf Hardware-Mikrofone zu.
