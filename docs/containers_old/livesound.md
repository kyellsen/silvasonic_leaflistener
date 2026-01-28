# Container: Livesound

## 1. Das Problem / Die Lücke
Wissenschaftler und Techniker müssen die Audioqualität der Mikrofone prüfen ("Ist das Rauschen Wind oder ein Defekt?"). Da die Recorder-Dateien erst nach Minuten abgeschlossen sind, ist ein direkter Feedback-Loop nicht möglich. Es wird eine Echtzeit-Streaming-Lösung benötigt, um "in den Wald hineinzuhören", ohne physisch dort zu sein.

## 2. Nutzen für den User
*   **Live-Monitoring:** Ermöglicht das Anhören der Mikrofone in Echtzeit via Web-Browser.
*   **Qualitätskontrolle:** Sofortiges Erkennen von Störungen, Übersteuerung oder Hardware-Defekten.
*   **Signal-Validierung:** Visualisierung der Signalstärke (RMS/Peak) hilft bei der Ausrichtung und Pegelung der Mikrofone.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **Audio Streams:** Empfängt Audio-Daten (z.B. via UDP/Socket Streams) von den laufenden Recordern.
    *   **Konfiguration:** Liest Port-Mappings und Quellen aus der Konfiguration.
*   **Processing:**
    *   **Aggregation:** Sammelt Streams von verschiedenen Quellen.
    *   **Webserver stack:** Nutzt Uvicorn/Starlette/FastAPI für das Streaming.
    *   **Stats:** Berechnet Echtzeit-Metriken (Signalpegel) für das Dashboard.
*   **Outputs:**
    *   **Audio Stream:** Stellt Endpunkte (HTTP/Websocket) bereit, die vom Audio-Player im Dashboard konsumiert werden.
    *   **Source Stats:** Liefert Status-Updates über aktive Streams an das System.

## 4. Abgrenzung (Out of Scope)
*   Speichert **KEINE** Aufnahmen dauerhaft (Aufgabe von `recorder`).
*   Analysiert **KEINE** Tierstimmen (Aufgabe von `birdnet`).
*   Bietet **KEINE** eigene grafische Oberfläche (ist ein Backend-Service für das `dashboard`).
