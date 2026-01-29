# Container: Monitor

## 1. Das Problem / Die Lücke
Wir brauchen einen zentralen "Wachhund", der schläft nie. Wenn ein Container ausfällt oder eine Fledermaus erkannt wird, muss jemand den User proaktiv informieren, ohne dass dieser permanent auf das Dashboard starrt.

## 2. Nutzen für den User
*   **Ruhe:** Das System meldet sich nur, wenn etwas wichtiges passiert.
*   **Sicherheit:** Sofortige Info, wenn ein Recorder ausfällt (z.B. Stromausfall, Kabelbruch).
*   **Flexibilität:** Unterstützt alle gängigen Messenger (Telegram, Signal, Discord, Email) via Apprise.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs**:
    *   **Heartbeats**: Überwacht Redis Keys (`status:*`) auf Aktualität.
    *   **Alerts**: Abonniert den Redis Pub/Sub Channel `alerts`.
*   **Processing**:
    *   **Watchdog**: Prüft alle 10s, ob Dienste überfällig sind (Timeouts konfiguriert, z.B. Recorder 120s).
    *   **Aggregation**: Fasst den Systemstatus zusammen (`system:status`) für das Dashboard.
*   **Outputs**:
    *   **Benachrichtigung**: Sendet Push-Notifications via Apprise-Bibliothek (basierend auf `settings.json` Secrets).
    *   **Status-Aggregation**: Schreibt `system:status` Key in Redis.

## 4. Abgrenzung (Out of Scope)
*   **Keine Reparatur:** Startet keine Container neu (Aufgabe des Controllers/Podman).
*   **Kein UI:** Hat keine eigene Weboberfläche.
