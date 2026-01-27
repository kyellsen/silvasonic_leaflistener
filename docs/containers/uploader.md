# Container: Uploader

## 1. Das Problem / Die Lücke
Die Audio-Daten werden lokal auf SSD gespeichert, aber Wissenschaftler benötigen sie zentral in der Cloud oder im Labor zur Analyse. Ein manuelles Kopieren per USB-Stick ist bei Feldgeräten unpraktikabel. Da Mobilfunkverbindungen instabil oder langsam sein können, darf der Upload-Prozess niemals den Recorder blockieren. Es wird ein robuster, asynchroner Mechanismus benötigt, der "Fire and Forget" ermöglicht.

## 2. Nutzen für den User
*   **Datensicherung:** Automatisches Backup der Aufnahmen auf einen externen Server (Nextcloud, S3, FTP).
*   **Remote-Zugriff:** Daten sind verfügbar, ohne physisch zum Gerät fahren zu müssen.
*   **Bandbreiten-Management:** Lädt im Hintergrund hoch, nutzt "Low Priority" QoS, um SSH-Zugriffe nicht zu verstopfen.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   Dateisystem (`/mnt/data/.../recordings`): Überwacht Ordner auf *fertige* Dateien (die nicht mehr vom Recorder geschrieben werden).
    *   Credentials: Zugangsdaten für den Ziel-Server (via Environment Variables / Rclone Config).
    *   Netzwerk-Verbindung.
*   **Processing:**
    *   Erkennung neuer Dateien.
    *   Wrapper um `rclone` oder interne Python-Sync-Logik.
    *   Retry-Mechanismen bei Netzwerkabbrüchen (Exponential Backoff).
    *   Integritätsprüfung (Checksums).
*   **Outputs:**
    *   Daten-Transfer (Upload) zum Ziel.
    *   (Optional) Löschen oder Markieren lokaler Dateien nach erfolgreichem Upload (Archivierungs-Flag).

## 4. Abgrenzung (Out of Scope)
*   Nimmt **KEIN** Audio auf.
*   Analysiert **KEINE** Daten.
*   Entscheidet **NICHT** über Disk-Cleanup bei vollem Speicher (das macht der `healthchecker` als "Last Resort", auch wenn der Uploader idealerweise Platz freigeben würde, ist die Notfall-Löschung getrennt).
