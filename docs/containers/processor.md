# Container: Processor

## 1. Das Problem / Die Lücke
Wir haben Rohdaten (WAV-Dateien), die auf der Festplatte landen, aber die Datenbank weiß davon nichts. Außerdem läuft die Festplatte irgendwann voll. Der Processor ist das "Gehirn" im Hintergrund, das Ordnung hält.

## 2. Nutzen für den User
*   **Daten-Integrität:** Stellt sicher, dass jede Aufnahme in der Datenbank findbar ist (Indexer).
*   **Visualisierung:** Erzeugt Ultraschall-Spektrogramme für Fledermäuse, die der Browser nicht nativ rendern kann.
*   **Sorgenfreiheit:** Der "Janitor" putzt automatisch die Festplatte, bevor sie voll läuft (löscht alte, bereits hochgeladene Dateien).

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs**:
    *   **Dateisystem:** Scannt `/data/recordings/{device_id}/{high_res|low_res}` auf neue WAV-Dateien.
*   **Processing**:
    *   **Indexer**: Erstellt DB-Einträge für neue Dateien.
    *   **Thumbnailer**: Generiert PNG-Spektrogramme für High-Res Aufnahmen (Fledermäuse).
    *   **Janitor**: Überwacht Speicherplatz (alle 5 Min).
        *   > 80%: Löscht sicher ("uploaded" & "analyzed").
        *   > 90%: Löscht Notfall-mäßig die ältesten Dateien.
*   **Outputs**:
    *   **Datenbank**: INSERT in `recordings` Tabelle. DELETE aus `recordings` Tabelle (bei Cleanup).
    *   **Thumbnails**: Speichert `.png` neben die `.wav` Dateien.
    *   **Benachrichtigung**: Sendet "New Recording" Events an Redis `alerts`.

## 4. Abgrenzung (Out of Scope)
*   **Keine Analyse:** Führt keine Artenerkennung durch (Job von BirdNET).
*   **Kein Upload:** Lädt nichts in die Cloud (Job des Uploaders).
