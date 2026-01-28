# Container: LiveSound

## 1. Das Problem / Die Lücke
Wissenschaftler und Techniker müssen die Audioqualität der Mikrofone prüfen ("Ist das Rauschen Wind oder ein Defekt?"). Da die Recorder-Dateien erst nach Minuten abgeschlossen sind, ist ein direkter Feedback-Loop nicht möglich. Es wird eine Echtzeit-Streaming-Lösung benötigt, um "in den Wald hineinzuhören", ohne physisch dort zu sein.

## 2. Nutzen für den User
*   **Live-Monitoring:** Ermöglicht das Anhören der Mikrofone in Echtzeit via Web-Browser.
*   **Qualitätskontrolle:** Sofortiges Erkennen von Störungen, Übersteuerung oder Hardware-Defekten.
*   **Signal-Validierung:** Visualisierung der Signalstärke (RMS/Peak) hilft bei der Ausrichtung und Pegelung der Mikrofone.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **Audio Streams:** Empfängt Audio-Daten (via UDP) von den laufenden Recordern.
    *   **Routing-Infos:** Liest Port-Mappings aus Status-Dateien des Controllers (`livesound_sources.json`), um zu wissen, wer sendet.
*   **Processing:**
    *   **Aggregation:** Bündelt die UDP-Streams verschiedener Mikrofone.
    *   **Streaming Server:** Nutzt FastAPI/Uvicorn, um Audio via HTTP/WebSocket an Clients zu streamen.
    *   **Signal-Analyse:** Berechnet Echtzeit-Metriken (Pegel) für die Anzeige im Dashboard.
*   **Outputs:**
    *   **Web-Streams:** Stellt Endpunkte bereit, die vom Audio-Player im Dashboard konsumiert werden.
    *   **Source Stats:** Meldet aktive Quellen und Signalstärken via Redis an das Dashboard.

## 4. Abgrenzung (Out of Scope)
*   Speichert **KEINE** Aufnahmen dauerhaft (Aufgabe von `recorder`).
*   Analysiert **KEINE** Tierstimmen (Aufgabe von `birdnet`).
*   Bietet **KEINE** eigene grafische Web-Oberfläche (dient als Backend-Service für das `dashboard`).
