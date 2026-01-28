# Container: Healthchecker

## 1. Das Problem / Die Lücke
In einem verteilten System operieren viele Container unabhängig voneinander. Ein einzelner Service (z.B. der Uploader) kann "leise sterben" (Deadlock, Endlosschleife), während der Container-Status laut Docker noch "Running" ist. Ohne Überwachung würde ein solcher Ausfall erst nach Tagen auffallen (Datenlücke). Es wird ein zentraler Wächter benötigt, der die Vitalfunktionen aller Services prüft.

## 2. Nutzen für den User
*   **Zuverlässigkeit:** Erkennt Probleme, bevor Daten verloren gehen (z.B. "Uploader lädt seit 1h nichts hoch").
*   **Wartung:** Automatisiert Routineaufgaben wie das Löschen verwaister Status-Dateien ("Ghost Recorders") oder Log-Rotation.
*   **Benachrichtigung:** Sendet Alerts (z.B. per E-Mail) bei kritischen Fehlern (Disk Full, Service Down) oder interessanten Funden (Vogel-Benachrichtigung).
*   **Consolidated Status:** Bietet dem Dashboard eine "Source of Truth" (`system_status.json`) über den gesamten Systemzustand.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **Status-Files:** Pollt regelmäßig das `status/`-Verzeichnis, wo alle Container ihre Heartbeats (`.json`) ablegen.
    *   **Notification Queue:** Überwacht `notifications/` auf neue Events (z.B. BirdNET Alerts).
    *   **Probes:** Führt aktive Checks durch (z.B. TCP Connect zu Postgres).
*   **Processing:**
    *   **Watchdog-Logik:** Vergleicht Zeitstempel der Heartbeats mit Timeouts (z.B. "Recorder muss sich alle 2 Min melden").
    *   **State Machine:** Erkennt Status-Übergänge (Running -> Down -> Recovered) und generiert entsprechende Logs/Alerts.
    *   **Mailer:** Versendet E-Mail-Benachrichtigungen bei Konfiguration.
    *   **Cleanup:** Löscht alte "Ghost"-Einträge von entfernten Mikrofonen.
*   **Outputs:**
    *   `system_status.json`: Eine aggregierte Übersicht für das Dashboard.
    *   **Alerts:** Ausgehende E-Mails oder gesicherte Fehlerberichte in `archive/`.

## 4. Abgrenzung (Out of Scope)
*   Startet/Stoppt **KEINE** Hardware-Container (Aufgabe von `controller`).
*   Überwacht **NICHT** den Kernel oder Host-OS-Crashes.
*   Speichert **KEINE** Audio-Daten.
