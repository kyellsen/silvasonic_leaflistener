# Container: BirdNET

## 1. Das Problem / Die Lücke
Die Analyse von Audiodaten mittels Deep Learning ist extrem ressourcenintensiv (CPU/RAM). Würde dieser Prozess synchron im Aufnahmethread (Recorder) laufen, käme es zu Audio-Dropouts ("Knacksern") oder Überlastung. Zudem benötigen KI-Modelle oft spezifische, große Abhängigkeiten (TensorFlow Lite), die man vom schlanken, stabilen Recorder-Container isolieren möchte ("Dependency Hell" vermeiden).

## 2. Nutzen für den User
*   **Automatische Arterkennung:** Verwandelt "stumme" .flac-Dateien in durchsuchbare Metadaten (Welcher Vogel? Wann? Wie sicher?).
*   **Asynchrone Verarbeitung:** Die Analyse kann langsamer als Echtzeit laufen (z.B. tagsüber aufnehmen, nachts "aufholen"), ohne die laufende Aufnahme zu gefährden.
*   **Modularität:** Das Erkennungsmodell kann aktualisiert oder ausgetauscht werden, ohne das kritische Aufnahmesystem zu berühren.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   Neue `.flac` Audio-Dateien (bereitgestellt via Shared Volume vom Recorder).
    *   Konfiguration (Schwellenwerte für Konfidenz, Geo-Location, Sensitivität) via `config.yml`, `settings.json` oder Environment-Variablen.
    *   BirdNET-Modell (`.tflite`) und Label-Dateien.
*   **Processing:**
    *   **Watcher Service:** Überwacht das Aufnahmeverzeichnis rekursiv auf neu geschlossene Dateien (`IN_CLOSE_WRITE`).
    *   **Preprocessing:** Resampling der Audiodaten (typisch auf 48kHz) und Segmentierung für das Modell.
    *   **Inferenz:** Führt das TensorFlow Lite Modell auf den Audio-Segmenten aus.
    *   **Filtering:** Wendet Filterlogik an (Minimum Confidence, Geo-Location Filter, Wochen-Filter).
*   **Outputs:**
    *   **Datenbank-Einträge:** Schreibt validierte Detektionen (Spezies, Zeitstempel, Konfidenz) direkt in die PostgreSQL Datenbank.
    *   **Clips (Optional):** Extrahiert kurze Audio-Schnipsel der Fundstellen (falls konfiguriert).
    *   **Logs:** Strukturiertes Logging über den Analyse-Fortschritt.

## 4. Abgrenzung (Out of Scope)
*   Macht **KEINE** Audio-Aufnahme (Aufgabe von `recorder`).
*   Macht **KEINEN** Upload der Dateien in die Cloud (Aufgabe von `uploader`).
*   Bietet **KEINE** Benutzeroberfläche zur Visualisierung (Aufgabe von `dashboard`).
*   Hört **NICHT** am Mikrofon.
