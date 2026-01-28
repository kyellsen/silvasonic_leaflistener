# Container: Uploader

## 1. Das Problem / Die Lücke
Aufgenommene Daten liegen zunächst isoliert auf dem Edge-Device im Wald. Um sie wissenschaftlich zu nutzen oder dauerhaft zu sichern, müssen sie auf einen zentralen Server transportiert werden. Da Mobilfunkverbindungen instabil sein können, darf dieser Prozess niemals die Aufnahme blockieren. Es wird ein robuster "Fire and Forget" Hintergrund-Dienst benötigt.

## 2. Nutzen für den User
*   **Datensicherung:** Schützt vor Datenverlust durch Hardware-Defekt oder Diebstahl des Geräts (Off-Site Backup).
*   **Fernzugriff:** Macht die Aufnahmen bequem im Labor/Büro verfügbar.
*   **Speichermanagement:** Der "Janitor" (Hausmeister) sorgt dafür, dass lokal Platz freigegeben wird, sobald Daten sicher in der Cloud liegen.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs:**
    *   **Recordings:** Überwacht das Aufnahmeverzeichnis auf neue, abgeschlossene Dateien.
    *   **Credentials:** Zugangsdaten für Cloud-Storage (Nextcloud/WebDAV/S3).
    *   **Konfiguration:** Upload-Strategie (z.B. "Nur im WLAN", "Sofort").
*   **Processing:**
    *   **Sync-Engine:** Nutzt `rclone` (oder kompatiblen Wrapper) für effizienten, wiederaufnehmbaren Datei-Transfer.
    *   **Queue-Management:** Berechnet die Warteschlange und schätzt die Upload-Dauer.
    *   **Janitor:** Löscht lokale Kopien *erst*, wenn der Upload verifiziert ist und der lokale Speicherplatz knapp wird (Threshold-basiert).
    *   **DB-Logging:** Führt Buch über jede hochgeladene Datei in der Datenbank.
*   **Outputs:**
    *   **Upload:** Transferiert Dateien an den Remote-Server.
    *   **Löschung:** Entfernt Dateien vom lokalen Datenträger (wenn konfiguriert).

## 4. Abgrenzung (Out of Scope)
*   Nimmt **KEIN** Audio auf.
*   Entscheidet **NICHT** über "Notfall-Löschungen" bei kritisch vollem Speicher (das ist die letzte Verteidigungslinie des `healthchecker`, der Uploader macht "sauberes" Aufräumen).
