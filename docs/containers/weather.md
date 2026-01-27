# Container: Weather

## 1. Das Problem / Die Lücke
Bioakustik ist stark wetterabhängig (Wind, Regen, Temperatur beeinflussen Tiervorkommen und Aufnahmequalität). Um wissenschaftliche Korrelationen herzustellen ("Ruft diese Art nur bei über 20°C?"), müssen Umgebungsdaten synchron zur Audioaufnahme erfasst werden. Externe Wetterdienste sind für Mikroklima-Daten zu ungenau.

## 2. Nutzen für den User
*   **Kontextualisierung:** Liefert Metadaten zur Audio-Aufnahme (Temp, Feuchte, Luftdruck).
*   **Hardware-Schutz:** Kann theoretisch genutzt werden, um das System bei extremer Hitze herunterzufahren (falls gekoppelt).
*   **Forschung:** Ermöglicht komplexere Analysen (Bioakustik vs. Meteorologie).

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   Hardware-Sensoren via I2C/GPIO (z.B. BME280 für Temp/Pressure/Humidity).
    *   (Optional) Externe APIs.
*   **Processing:**
    *   Auslesen der Sensoren in definierten Intervallen.
    *   Plausibilitätsprüfung der Messwerte.
*   **Outputs:**
    *   Datenbank-Einträge (Zeitreihe der Wetterdaten).
    *   Bereitstellung für Dashboard-Widgets.

## 4. Abgrenzung (Out of Scope)
*   Nimmt **KEIN** Audio auf.
*   Ist **KEINE** Wettervorhersage (nur Ist-Zustand).
*   **Status:** Dieser Container ist in vielen Deployments **deaktiviert** oder optional, da er spezifische Hardware-Sensoren erfordert.
