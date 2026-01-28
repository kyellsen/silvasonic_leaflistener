# Container: Weather

## 1. Das Problem / Die Lücke
Bioakustische Aktivität korreliert stark mit Wetterbedingungen (Temperatur, Wind, Regen). Eine "stille" Nacht kann an der Abwesenheit von Vögeln liegen – oder einfach an starkem Regen, der die Tiere schweigen lässt. Ohne Wetterdaten fehlt dieser Kontext. Reine Audioaufnahmen erzählen nur die halbe Geschichte.

## 2. Nutzen für den User
*   **Wissenschaftlicher Kontext:** Ermöglicht Korrelationsanalysen ("Ruft Spezies X nur bei >15°C?").
*   **Datenqualität:** Hilft, Fehl-Detektionen zu erklären (z.B. starker Wind erzeugt Rauschen im Spektrogramm).
*   **Lückenfüllung:** Erfasst Daten auch dann, wenn keine externe Wetterstation in der Nähe ist (nutzt OpenMeteo API für den Standort oder lokale Sensoren).

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **OpenMeteo API:** Holt aktuelle Wetterdaten (Temp, Feuchte, Niederschlag, Wind, Wolkendecke) basierend auf den Geo-Koordinaten.
    *   **(Optional) Sensoren:** Könnte Hardware-Sensoren (BME280) auslesen (in dieser Implementierung primär API-basiert).
*   **Processing:**
    *   **Scheduler:** Führt den Abruf in regelmäßigen Intervallen aus (z.B. alle 20 Minuten).
    *   **Daten-Normalisierung:** Wandelt API-Antworten in ein standardisiertes Datenmodell (`WeatherMeasurement`).
*   **Outputs:**
    *   **Datenbank:** Schreibt die Messwerte persistent in die PostgreSQL-Tabelle `weather.measurements`.
    *   **Status:** Meldet Aktivität an das System via Heartbeat.

## 4. Abgrenzung (Out of Scope)
*   Nimmt **KEIN** Audio auf.
*   Erstellt **KEINE** eigene Vorhersage (nutzt existierende Datenquellen/Sensoren).
*   Beeinflusst **NICHT** die Aufnahme-Steuerung (dient rein der Datenerfassung).
