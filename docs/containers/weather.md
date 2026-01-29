# Container: Weather

## 1. Das Problem / Die Lücke
Biologische Aktivität hängt stark vom Wetter ab. Fledermäuse fliegen nicht bei Sturm. Um später Zusammenhänge zu erkennen ("Keine Aufnahme weil defekt oder weil Regen?"), benötigen wir lokale Wetterdaten synchron zur Aufnahme.

## 2. Nutzen für den User
*   **Kontext:** Zeigt im Dashboard Temperatur, Wind und Regen neben den Aufnahmen an.
*   **Wissenschaft:** Ermöglicht Korrelationsanalysen (z.B. "Pipistrellus fliegt erst ab 12°C").
*   **Keine Hardware:** Nutzt die OpenMeteo-API (GPS-basiert), benötigt also keine physische Wetterstation.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs**:
    *   **API**: Fragt `api.open-meteo.com` ab (basierend auf GPS-Koordinaten in `settings.json`).
*   **Processing**:
    *   **Scheduler**: Läuft alle 20 Minuten.
    *   **Modellierung**: Mappt JSON-Antwort auf `WeatherMeasurement` Modell.
*   **Outputs**:
    *   **Datenbank**: Schreibt in die `measurements` Tabelle.
    *   **Status**: Meldet Status an Redis.

## 4. Abgrenzung (Out of Scope)
*   **Keine Vorhersage:** Speichert nur *aktuelle* Werte (bzw. "Current" Endpoint), keine Prognosen für morgen.
*   **Kein Sensor:** Liest keine lokalen USB-Sensoren aus.
