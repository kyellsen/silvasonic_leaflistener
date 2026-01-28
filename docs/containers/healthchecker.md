# Container: Healthchecker

## 1. Das Problem / Die Lücke
In einem verteilten System können einzelne Services ausfallen ("Silent Fail"), ohne dass der Container stoppt. Ein zentraler Wächter ist notwendig, um solche "Zombie-Prozesse" zu erkennen, Timeouts zu überwachen und den Administrator proaktiv zu informieren.

## 2. Nutzen für den User
*   **Zuverlässigkeit:** Erkennt Probleme (z.B. Recorder sendet keinen Heartbeat mehr) sofort.
*   **Alerting:** Benachrichtigt aktiv via E-Mail bei kritischen Fehlern oder interessanten Funden (Vogel-Detektionen).
*   **Status-Sicht:** Liefert dem Dashboard aggregierte Gesundheitsdaten aller Komponenten.
*   **Wartung:** Archiviert Fehlerberichte und hält das System sauber.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **Redis Heartbeats:** Pollt periodisch `status:*` Keys aller Services.
    *   **Notification Queue:** Überwacht `notifications/` auf neue Events (z.B. BirdNET Alerts).
    *   **Service Config:** Liest Timeouts und Regeln aus `settings.json`.
*   **Processing:**
    *   **Watchdog:** Vergleicht "Last Seen" Zeitstempel mit konfigurierten Timeouts.
    *   **State Machine:** Detektiert Statuswechsel (Running -> Down) und vermeidet Alert-Spam.
    *   **Mailer:** Versendet formatierte E-Mails via SMTP (`apprise` library).
*   **Outputs:**
    *   **System Status:** Schreibt aggregierten Status nach Redis (`system:status`) und File (Legacy).
    *   **Alerts:** Versendet E-Mails.
    *   **Archive:** Verschiebt verarbeitete Fehlerberichte nach `archive/`.

## 4. Abgrenzung (Out of Scope)
*   Startet **KEINE** Container neu (Aufgabe von `controller`).
*   Speichert **KEINE** Audiodaten.
*   Ist **NICHT** für Hardware-Monitoring zuständig (Layer darüber).
