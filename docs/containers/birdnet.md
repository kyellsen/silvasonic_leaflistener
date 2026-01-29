# Container: BirdNET

## 1. Das Problem / Die Lücke
Dieses Modul integriert die akustische Artenerkennung für Vögel in das System. Da BirdNET rechenintensiv ist und spezifische Abhängigkeiten (TensorFlow/TFLite Model) benötigt, wird es als isolierter Worker betrieben, um die Stabilität des Kernsystems (Aufnahme) nicht zu gefährden.

## 2. Nutzen für den User
*   **Automatische Klassifizierung:** Erkennt Vogelarten in den Aufnahmen.
*   **Filterung:** Ermöglicht das gezielte Suchen nach Arten im Dashboard.
*   **Benachrichtigung:** Löst Alarme bei Sichtung spezifischer Arten (Watchlist) aus.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs**:
    *   Datenbank-Polling: Fragt `recordings` Tabelle ab (`WHERE analyzed_bird = false`).
    *   Audio-Dateien: Liest `.wav` Dateien (bevorzugt 48kHz "Low High" Pfad) vom geteilten Volume (`/data/recordings`).
    *   Watchlist: Liest `watchlist` Tabelle für Alarm-Kriterien.
*   **Processing**:
    *   **Resampling**: Konvertiert Input temporär via `ffmpeg` zu 48kHz Mono.
    *   **Inferenz**: Führt das BirdNET-Analyzer Modell aus.
    *   **Clip-Extraktion**: Schneidet erkannte Sequenzen (mit Padding) als separate `.wav` Clips aus.
*   **Outputs**:
    *   **Datenbank**: Schreibt Erkennungen in die `detections` Tabelle.
    *   **Status-Update**: Setzt `analyzed_bird = true` in der `recordings` Tabelle.
    *   **Dateien**: Speichert Audio-Clips im konfigurierten Clips-Verzeichnis.
    *   **Benachrichtigung**: Generiert JSON-Event-Dateien in `/data/notifications` (für den Monitor/Notifier).

## 4. Abgrenzung (Out of Scope)
*   **Keine Aufnahme:** Nimmt kein Audio auf (Aufgabe des Recorders).
*   **Kein Live-Audio:** Analysiert nur abgeschlossene Dateien, keinen Live-Stream.
*   **Kein Versand:** Versendet keine E-Mails/Telegram-Nachrichten (Aufgabe des Monitors via Apprise).
