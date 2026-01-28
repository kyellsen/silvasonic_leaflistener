# Container: Healthchecker

## 1. Das Problem / Die Lücke
In einem verteilten System operieren viele Container unabhängig voneinander. Ein einzelner Service (z.B. der Uploader) kann "leise sterben" (z.B. Deadlock), während der Container-Status noch "Running" ist. Ohne proaktive Überwachung würde ein solcher Ausfall erst spät auffallen (Datenlücke). Es wird ein zentraler "Wächter" benötigt.

## 2. Nutzen für den User
*   **Zuverlässigkeit:** Erkennt Probleme frühzeitig (z.B. "Recorder hat seit 2 Minuten keinen Heartbeat gesendet").
*   **Wartung:** Automatisiert Routineaufgaben wie Log-Rotation oder Benachrichtigungen.
*   **Alerting:** Sendet proaktiv E-Mails bei kritischen Fehlern (Disk Full, Service Down) oder interessanten Vogel-Funden.
*   **Status-Aggregation:** Liefert dem Dashboard eine konsolidierte Sicht auf die Systemgesundheit.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **Redis Heartbeats:** Pollt regelmäßig den Key-Space `status:*` in Redis, wo alle aktiven Services ihren Puls melden.
    *   **Notification Queue:** Überwacht das Verzeichnis `notifications/` auf neue Events (z.B. BirdNET Alerts).
    *   **Active Probes:** Prüft TCP-Verbindung zur Datenbank.
*   **Processing:**
    *   **Watchdog-Logik:** Vergleicht Zeitstempel der Heartbeats mit definierten Timeouts (z.B. "Recorder timeout = 120s").
    *   **State Machine:** Erkennt Status-Übergänge (z.B. Running -> Down) und triggert Alerts nur bei Änderungen, um Spam zu vermeiden.
    *   **Mailer:** Versendet E-Mail-Benachrichtigungen via SMTP.
*   **Outputs:**
    *   **System Status:** Schreibt den aggregierten Status zurück nach Redis (`system:status`) und als JSON-Datei (Legacy Support).
    *   **E-Mails:** Sendet Warnungen und Berichte an konfigurierte Empfänger.

## 4. Abgrenzung (Out of Scope)
*   Startet/Stoppt **KEINE** Container (Aufgabe von `controller`).
*   Überwacht **NICHT** den Kernel (nur die Applikations-Ebene).
*   Speichert **KEINE** Audio-Daten.
