# Container: silvasonic_weather

## 1. Das Problem / Die Lücke
Bioakustische Daten sind alleinstehend oft schwer zu interpretieren. "Keine Fledermäuse in dieser Nacht" kann an fehlender Population oder einfach an starkem Regen liegen. Wir brauchen Umwelt-Kontext. Lokale Sensoren sind oft teuer oder wartungsintensiv.

## 2. Nutzen für den User
*   **Kontext**: Korreliert Tieraktivität automatisch mit Wetterdaten (Temperatur, Wind, Regen).
*   **Wartungsfrei**: Nutzt virtuelle Sensoren (Open-Data APIs) statt Hardware.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs**:
    *   **OpenMeteo API**: Ruft Wetterdaten für die konfigurierte GPS-Position ab.
*   **Processing**:
    *   Standardisierung der Daten.
    *   Zeitplan-Management (z.B. alle 20 Minuten).
*   **Outputs**:
    *   **Datenbank**: Speichert Werte in Tabelle `measurements`.

## 4. Abgrenzung (Out of Scope)
*   **Keine Hardware**: Liest keine physischen Sensoren (DHT22 etc.) aus.
*   **Keine Vorhersage**: Speichert "Current Weather" (Ist-Zustand), keine Forecasts für die Zukunft.

## 5. Technologien die dieser Container nutzt
*   **Basis-Image**: Python 3.11+
*   **Wichtige Komponenten**:
    *   `httpx` (HTTP Client)
    *   `schedule` (Loop)
    *   `sqlalchemy` (DB Write)

## 6. Kritische Punkte
*   **API Limits**: OpenMeteo ist free, aber hat Rate Limits. Der Intervall darf nicht zu kurz sein (z.B. < 1 Minute). 20 Minuten ist ein guter Kompromiss.
*   **Internetpflicht**: Ohne Internetverbindung keine Wetterdaten.
