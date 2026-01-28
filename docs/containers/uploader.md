# Container: Uploader

## 1. Das Problem / Die Lücke
Aufgenommene Daten liegen zunächst isoliert auf dem Edge-Device. Für die wissenschaftliche Nutzung und Langzeitarchivierung müssen sie auf einen zentralen Server übertragen werden. Da Mobilfunkverbindungen unzuverlässig sind, darf dies nie die Aufnahme blockieren. Es wird ein robuster, asynchroner Hintergrunddienst ("Fire & Forget") benötigt.

## 2. Nutzen für den User
*   **Datensicherheit:** Schützt vor Datenverlust durch Hardware-Defekt oder Diebstahl (Off-Site Backup).
*   **Fernzugriff:** Macht Aufnahmen im Labor verfügbar, ohne SD-Karten physisch tauschen zu müssen.
*   **Speichermanagement:** Der integrierte "Janitor" löscht lokal, sobald Dateien sicher in der Cloud sind, um Platz für neue Aufnahmen zu schaffen.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **Recordings:** Scannt `/data/recording` rekursiv auf neue Dateien.
    *   **Konfiguration:** Upload-Strategien (z.B. "Nur WLAN", "Min. Alter") aus `config.py`.
    *   **Credentials:** Zugriff auf S3/Nextcloud/WebDAV via Environment Secrets.
*   **Processing:**
    *   **Sync-Engine:** Nutzt `rclone` (wrapper) für effiziente, wiederaufnehmbare Transfers.
    *   **Queue-Management:** Priorisiert Uploads und verwaltet Retries bei Netzwerkausfall.
    *   **Janitor:** Löscht lokale Kopien erst nach erfolgreicher Upload-Verifikation und bei Speicherbedarf.
    *   **Logging:** Protokolliert Transaktionen in der Datenbank.
*   **Outputs:**
    *   **Upload:** Transferiert Dateien verschlüsselt an den Remote-Storage.
    *   **Status:** Meldet Fortschritt und Queue-Größe an Redis.

## 4. Abgrenzung (Out of Scope)
*   Nimmt **KEIN** Audio auf (-> `recorder`).
*   Analysiert **KEINE** Daten (-> `birdnet`).
*   Löscht **NICHTS** ohne Upload-Bestätigung (Datenverlust-Schutz hat Vorrang).
