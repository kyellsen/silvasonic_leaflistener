# Container: Healthchecker

## 1. Das Problem / Die Lücke
In einem verteilten System aus unabhängigen Containern kann ein einzelner Service (z.B. der Uploader) hängen bleiben, ohne dass der Rest des Systems es merkt. Ein "stiller Tod" eines Containers würde bedeuten, dass tagelang keine Daten hochgeladen werden. Es wird eine unabhängige Instanz benötigt, die das Gesamtsystem überwacht und bei Problemen eingreifen oder alarmieren kann.

## 2. Nutzen für den User
*   **Selbstheilung:** Das System versucht, hängende Dienste automatisch neu zu starten (falls konfiguriert).
*   **Wartung:** Übernimmt Aufgaben wie Log-Rotation und Bereinigung alter Dateien, damit die Festplatte nicht vollläuft.
*   **Benachrichtigung:** Informiert den User über kritische Zustände (z.B. Disk Full).

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   Docker/Podman Socket (zum Abfragen des Container-Status).
    *   System-Ressourcen (Disk Usage, RAM).
    *   HTTP-Health-Endpoints der anderen Services.
*   **Processing:**
    *   Periodische Checks (z.B. alle 60 Sekunden): "Läuft der Recorder?", "Ist die DB erreichbar?".
    *   Watchdog-Logik: Neustart von Containern, die als "unhealthy" markiert sind.
    *   Disk-Management: Löschen ältester Aufnahmen, wenn Speicherplatz-Limit erreicht (Retention Policy).
*   **Outputs:**
    *   Logs/Alerts.
    *   Kommandos an den Docker/Podman Daemon (Restart).

## 4. Abgrenzung (Out of Scope)
*   Startet **NICHT** die Hardware initial (Aufgabe von `controller`).
*   Ersetzt **NICHT** das Monitoring des Host-OS (Systemd/Kernel Panic).
*   Speichert **KEINE** Audio-Daten.
