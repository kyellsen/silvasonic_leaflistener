# Container: Uploader

## 1. Das Problem / Die Lücke
384kHz WAV-Dateien sprengen schnell jede Internetleitung und jeden Cloud-Speicher. Eine Live-Komprimierung während der Aufnahme ist aber zu riskant für die CPU.

## 2. Nutzen für den User
*   **Datensicherung:** Lädt Aufnahmen vollautomatisch in die Cloud (Google Drive, S3, Nextcloud, etc.).
*   **Effizienz:** Komprimiert WAV zu FLAC (~50% Größe) *vor* dem Upload, spart Bandbreite.
*   **Entkopplung:** Läuft im Hintergrund mit niedriger Priorität ("Nice"), stört weder Aufnahme noch Analyse.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs**:
    *   **Datenbank**: Fragt `recordings` nach Dateien mit `uploaded=false`.
    *   **Dateisystem**: Liest Quelldateien (bevorzugt High-Res).
*   **Processing**:
    *   **Komprimierung**: Wandelt WAV temporär in FLAC um (ffmpeg, Level 5).
    *   **Upload**: Nutzt `rclone` für maximalen Protokoll-Support (SFTP, S3, WebDAV, etc.).
*   **Outputs**:
    *   **Cloud**: Datei landet im Ziel.
    *   **Datenbank**: Setzt `uploaded=true` (Signal für Janitor zum späteren Löschen).

## 4. Abgrenzung (Out of Scope)
*   **Kein Löschen:** Löscht niemals Originaldateien (das macht der Processor/Janitor).
*   **Keine Konfiguration:** Die Rclone-Config muss vom User (einmalig) im `config` Verzeichnis bereitgestellt werden.
