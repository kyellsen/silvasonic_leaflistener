# Container: silvasonic_monitor

## 1. Das Problem / Die Lücke
In einem verteilten System aus vielen Containern können einzelne Dienste "heimlich" sterben (z.B. Recorder hängt), ohne dass der User, der nicht ständig aufs Dashboard schaut, es merkt. Ein "Silent Failure" ist bei Langzeit-Monitoring katastrophal.

## 2. Nutzen für den User
*   **Seelenfrieden**: Der User wird aktiv benachrichtigt (Telegram, Email, Gotify), wenn etwas schief läuft.
*   **System-Übersicht**: Aggregiert den Gesundheitszustand aller Container für das Dashboard.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs**:
    *   **Redis Heartbeats**: Liest Schlüssel `status:*` (Polling).
    *   **Redis PubSub**: Abonniert Kanal `alerts` (Echtzeit-Events).
*   **Processing**:
    *   **Watchdog**: Vergleicht Zeitstempel der Heartbeats mit definierten Timeouts (z.B. Recorder > 120s = DOWN).
    *   **Aggregation**: Fasst den Status aller Dienste unter `system:status` zusammen.
    *   **Dispatch**: Leitet Benachrichtigungen via Apprise weiter.
*   **Outputs**:
    *   **Notifications**: Externe API-Calls (Telegram, SMTP, etc.).
    *   **Redis**: Aktualisiert `system:status` für das Dashboard.

## 4. Abgrenzung (Out of Scope)
*   **Kein Restart**: Startet keine Container neu (Aufgabe des Controllers oder Systemd).
*   **Keine Log-Analyse**: Liest (derzeit) keine Text-Logs, verlässt sich nur auf Heartbeats.

## 5. Technologien die dieser Container nutzt
*   **Basis-Image**: Python 3.11+
*   **Wichtige Komponenten**:
    *   `apprise` (Unified Notification Library)
    *   `redis`

## 6. Kritische Punkte
*   **Config Secrets**: Benötigt Zugriff auf `APPRISE_URLS` (mit Tokens/Passwörtern). Diese müssen sicher via Environment Variables injiziert werden.
*   **False Positives**: Zu aggressive Timeouts können zu Alarm-Spam führen, wenn das System unter Last nur kurzzeitig langsam ist.
