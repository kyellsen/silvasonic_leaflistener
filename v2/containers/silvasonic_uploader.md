# Container: silvasonic_uploader

## 1. Das Problem / Die Lücke
Der lokale Speicher (NVMe/SD) ist endlich. Für ein Langzeit-Projekt müssen Daten "offsite" bewegt werden, sowohl als Backup als auch zur dauerhaften Archivierung. WAV-Dateien sind zudem groß und verschwenden Bandbreite.

## 2. Nutzen für den User
*   **Unendlicher Speicher**: Durch automatischen Upload in die Cloud (S3, Dropbox, Nextcloud) läuft das lokale System nie voll (in Kombination mit dem Janitor).
*   **Effizienz**: Komprimiert verlustfrei zu FLAC (ca. 50% Ersparnis) *vor* dem Upload.
*   **Datensicherheit**: Schutz vor Diebstahl oder Defekt des Geräts.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs**:
    *   **Datenbank**: Polling `recordings WHERE uploaded=false`.
    *   **Dateisystem**: Liest WAV-Dateien.
*   **Processing**:
    *   **Compression**: Konvertiert WAV -> FLAC (ffmpeg).
    *   **Transport**: Lädt Dateien via Rclone hoch (`rclone copy`).
*   **Outputs**:
    *   **Cloud Storage**: Dateien im Ziel-Bucket.
    *   **Datenbank**: Setzt `uploaded=true`.

## 4. Abgrenzung (Out of Scope)
*   **Kein Löschen**: Löscht KEINE lokalen Original-Dateien aus `/data/recordings` (außer temporäre FLACs). Das Löschen ist Hoheit des `silvasonic_processor` (Janitor).
*   **Kein Sync**: Einweg-Upload ("Push"), kein bidirektionaler Sync.

## 5. Technologien die dieser Container nutzt
*   **Basis-Image**: Python 3.11+ (mit `ffmpeg` und `rclone`).
*   **Wichtige Komponenten**:
    *   `rclone` (Das "Schweizer Taschenmesser" für Cloud Storage)
    *   `ffmpeg` (Flac Encoder)
    *   `python` (Logik & DB-Anbindung)

## 6. Kritische Punkte
*   **Bandbreite**: Kann die Internetverbindung "verstopfen". Sollte idealerweise Bandbreiten-Limits (Rclone flag `--bwlimit`) oder Zeitfenster (z.B. "Nur Nachts") unterstützen (via Settings).
*   **Datenbank-Konsistenz**: Muss sicherstellen, dass `uploaded=true` erst gesetzt wird, wenn Rclone Erfolg meldet (Exit Code 0).
