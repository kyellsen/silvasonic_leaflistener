# Container: Weather

## 1. Das Problem / Die Lücke
Bioakustische Aktivität korreliert stark mit dem Wetter (Wind, Regen, Temperatur). Eine "stille" Aufnahme kann an der Abwesenheit von Tieren liegen – oder an starkem Sturm. Ohne Wetterdaten fehlt dieser Kontext. Reine Audioaufnahmen erzählen nur die halbe Geschichte.

## 2. Nutzen für den User
*   **Kontext:** Erklärt Artefakte (z.B. Windrauschen) und korreliert Tierstimmen mit Umweltbedingungen ("Ruft Spezies X nur bei Regen?").
*   **Lückenfüllung:** Erfasst Wetterdaten auch ohne physische Sensoren am Gerät (nutzt OpenMeteo API basierend auf GPS).
*   **Datenqualität:** Validiert akustische Detektionen durch Umweltparameter.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **OpenMeteo API:** Holt Wetterdaten (Temp, Wind, Regen etc.) via HTTP.
    *   **Schedule:** Läuft periodisch (alle 20 Minuten).
*   **Processing:**
    *   **Scheduler:** Triggered den Abruf zeitgesteuert.
    *   **Normalisierung:** Wandelt JSON-Antworten in das `WeatherMeasurement` Format.
*   **Outputs:**
    *   **Datenbank:** Schreibt Messwerte persistent in die Tabelle `weather.measurements` (PostgreSQL).
    *   **Status:** Meldet "Idle" oder "Fetching" via Redis (`status:weather`).

## 4. Abgrenzung (Out of Scope)
*   Nimmt **KEIN** Audio auf.
*   Erstellt **KEINE** Vorhersagen (nutzt externe Daten).
*   Hat **KEINE** eigenen Sensoren (Soft-Sensor).
