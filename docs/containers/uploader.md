# Container: Uploader

## 1. Das Problem / Die Lücke
Aufgenommene Daten liegen zunächst isoliert auf dem Edge-Device. Um sie sicher zu speichern und wissenschaftlich zu nutzen, müssen sie auf einen zentralen Server übertragen werden. Da Mobilfunkverbindungen unzuverlässig sind, darf dieser Prozess nie die Aufnahme blockieren. Es wird ein asynchroner, robuster Hintergrunddienst benötigt ("Fire and Forget").

## 2. Nutzen für den User
*   **Datensicherheit:** Schützt vor Datenverlust durch Hardware-Defekt oder Diebstahl (Off-Site Backup).
*   **Fernzugriff:** Macht Aufnahmen bequem im Labor/Büro verfügbar, ohne SD-Karten physisch tauschen zu müssen.
*   **Speichermanagement:** Der "Janitor" (Hausmeister) löscht automatisch alte lokale Dateien, sobald sie sicher hochgeladen wurden, um Speicherplatz freizugeben.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **Recordings:** Scannt das lokale Aufnahmeverzeichnis `/data/recording` rekursiv.
    *   **Konfiguration:** Liest Upload-Strategien (z.B. "Nur im WLAN", Mindestalter der Dateien) aus `UploaderSettings`.
    *   **Credentials:** Authentifizierung für Cloud-Storage (Nextcloud/WebDAV/S3) via Environment Secrets.
*   **Processing:**
    *   **Sync-Engine:** Nutzt `rclone` für effiziente, wiederaufnehmbare Datei-Transfers.
    *   **Queue-Management:** Berechnet die Warteschlange und priorisiert Uploads.
    *   **Janitor:** Löscht lokale Kopien *erst*, wenn der Upload verifiziert ist und Speicherplatz benötigt wird (Threshold-basiert).
    *   **Logging:** Protokolliert jeden Transfer in der lokalen Datenbank für Audit-Zwecke.
*   **Outputs:**
    *   **Upload:** Transferiert Dateien verschlüsselt an den Remote-Server.
    *   **Status:** Meldet Fortschritt und Queue-Größe via Redis an das Dashboard.

## 4. Abgrenzung (Out of Scope)
*   Nimmt **KEIN** Audio auf.
*   Entscheidet **NICHT** über "Notfall-Löschungen" bei kritisch vollem Speicher (Aufgabe des `healthchecker`, der Uploader agiert präventiv/ordentlich).
