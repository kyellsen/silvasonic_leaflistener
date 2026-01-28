# Container: Weather

## 1. Das Problem / Die Lücke
Bioakustische Aktivität korreliert stark mit Wetterbedingungen. Eine "stille" Aufnahme kann an der Abwesenheit von Tieren liegen – oder an starkem Wind/Regen. Ohne Wetterdaten fehlt dieser Kontext. Reine Audioaufnahmen erzählen nur die halbe Geschichte.

## 2. Nutzen für den User
*   **Wissenschaftlicher Kontext:** Ermöglicht Korrelationsanalysen ("Ruft Spezies X nur bei >15°C?").
*   **Datenqualität:** Hilft, Fehl-Detektionen oder schlechte Audioqualität (Windrauschen) zu erklären.
*   **Lückenfüllung:** Erfasst Umweltdaten auch ohne physische Sensoren am Gerät (nutzt OpenMeteo API basierend auf GPS-Koordinaten).

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **OpenMeteo API:** Holt aktuelle Wetterdaten (Temp, Feuchte, Niederschlag, Wind) für den Standort des Geräts.
    *   **Schedule:** Trigger alle 20 Minuten (konfigurierbar).
*   **Processing:**
    *   **Daten-Normalisierung:** Wandelt API-Antworten in das standardisierte `WeatherMeasurement` Datenmodell um.
    *   **Scheduler:** Führt den Abruf periodisch aus, unabhängig von anderen System-Events.
*   **Outputs:**
    *   **Datenbank:** Schreibt Messwerte persistent in die PostgreSQL-Tabelle `weather.measurements`.
    *   **Status:** Meldet "Idle" oder "Fetching" via Redis.

## 4. Abgrenzung (Out of Scope)
*   Nimmt **KEIN** Audio auf.
*   Erstellt **KEINE** eigene Wettervorhersage (nutzt externe Provider).
*   Beeinflusst **NICHT** die Aufnahme-Steuerung (dient rein der Datenerfassung).
