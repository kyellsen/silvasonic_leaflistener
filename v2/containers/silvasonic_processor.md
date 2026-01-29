# Container: silvasonic_processor

## 1. Das Problem / Die Lücke
Das reine Schreiben von Dateien auf die Festplatte (durch den Recorder) macht diese noch nicht durchsuchbar. Wir benötigen einen Prozess, der das Dateisystem überwacht, Metadaten in die Datenbank schreibt und "Housekeeping" betreibt, damit die Festplatte nicht vollläuft.

## 2. Nutzen für den User
*   **Ordnung**: Alle Aufnahmen erscheinen automatisch im Dashboard/Datenbank.
*   **Visualisierung**: Erstellt Spektrogramm-Vorschaubilder (Thumbnails) für Fledermaus-Aufnahmen, die der Browser nicht nativ rendern kann.
*   **Sorgenfreiheit**: Der "Janitor" löscht automatisch alte Dateien, bevor der Platz ausgeht.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs**:
    *   **Filesystem**: Polling auf `/data/recordings/`.
    *   **Datenbank**: Status-Checks (z.B. "Was ist das älteste File?").
*   **Processing**:
    *   **Indexer**: Erkennt neue WAV-Dateien, extrahiert Zeitstempel aus dem Dateinamen, schreibt Metadaten (Pfad, Zeit, Device) in DB `recordings`.
    *   **Thumbnailer**: Generiert PNG-Spektrogramme via `librosa/matplotlib` (CPU-intensiv, daher asynchron).
    *   **Janitor**: Überprüft Disk-Usage. Löscht Dateien basierend auf Regeln (Bereits hochgeladen? Zu alt? Disk voll?).
*   **Outputs**:
    *   **Datenbank**: `INSERT INTO recordings`.
    *   **Dateisystem**: Löschen von Dateien (`rm`).
    *   **Redis**: `alerts` (z.B. "Disk Full Warning").

## 4. Abgrenzung (Out of Scope)
*   **Keine Artenerkennung**: Klassifiziert keine Tiere (das macht BirdNET/BatDetect).
*   **Kein Recording**: Nimmt kein Audio auf.
*   **Kein Upload**: Schiebt nichts in die Cloud.

## 5. Technologien die dieser Container nutzt
*   **Basis-Image**: Python 3.11+
*   **Wichtige Komponenten**:
    *   `watchdog` (oder Polling Loop) für File-Events
    *   `psycopg2` (Datenbank Access)
    *   `librosa` + `matplotlib` (Audio Visualisierung)
    *   `redis` (Alerts)

## 6. Kritische Punkte
*   **Race Conditions**: Muss sicherstellen, dass er keine Datei indiziert/löscht, die gerade noch vom Recorder geschrieben wird. (Lösung: File-Locking oder Delay Checks).
*   **Performance**: Die Generierung von Spektrogrammen ("Thumbnailer") ist sehr CPU-lastig. Muss ggf. gedrosselt werden, um Recording nicht zu stören (`nice` Levels).
