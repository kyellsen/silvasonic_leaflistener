# Container: LiveSound

## 1. Das Problem / Die Lücke
Wissenschaftler müssen die Audioqualität der Mikrofone im Feld prüfen ("Ist das Rauschen Wind oder ein Defekt?"), ohne auf die abgeschlossenen Aufnahmedateien warten zu müssen. Es wird eine Echtzeit-Streaming-Lösung benötigt, um remote "in den Wald hineinzuhören".

## 2. Nutzen für den User
*   **Live-Monitoring:** Ermöglicht das Anhören der Mikrofone in Echtzeit via Web-Browser.
*   **Qualitätskontrolle:** Sofortiges Erkennen von Störungen, Übersteuerung oder Hardware-Defekten.
*   **Signal-Validierung:** Visualisierung der Signalstärke (RMS/Peak) hilft bei der Ausrichtung der Mikrofone.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **Audio Streams:** Empfängt Audio-Daten (via UDP) von den laufenden Recordern.
    *   **Routing-Infos:** Liest Port-Mappings aus Status-Dateien des Controllers (`livesound_sources.json`) oder Redis.
*   **Processing:**
    *   **Aggregation:** Bündelt die UIDP-Streams verschiedener Mikrofone.
    *   **Streaming Server:** Uvicorn/FastAPI liefert Audio via HTTP/WebSocket aus.
    *   **Signal-Analyse:** Berechnet Echtzeit-Metriken (Pegel) für die Anzeige.
*   **Outputs:**
    *   **Web-Streams:** Stellt Audio-Endpunkte bereit, die vom Dashboard konsumiert werden.
    *   **Source Stats:** Meldet aktive Quellen und Signalstärken via Redis (`status:livesound`).

## 4. Abgrenzung (Out of Scope)
*   Speichert **KEINE** Aufnahmen dauerhaft (-> `recorder`).
*   Analysiert **KEINE** Tierstimmen (-> `birdnet`).
*   Bietet **KEINE** eigene GUI (Backend für `dashboard`).
