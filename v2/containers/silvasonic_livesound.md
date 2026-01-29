# Container: silvasonic_livesound

## 1. Das Problem / Die Lücke
Browser unterstützen kein direktes Streaming von Roh-PCM-Daten (WAV) über lange Zeiträume effizient und stabil. Es wird ein dedizierter Streaming-Server benötigt, um Audio an viele Clients zu verteilen.

## 2. Nutzen für den User
*   **Live-Hören**: Ermöglicht das Reinhören in das Mikrofon in Echtzeit (via MP3/Opus Stream) über das Dashboard oder externe Player (VLC).
*   **Stabilität**: Pufferung gegen Netzwerk-Schwankungen.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs**:
    *   Audio-Source Stream vom `recorder` (via TCP, Icecast Protokoll).
*   **Processing**:
    *   Pufferung und Multiplexing des Streams an mehrere Listener.
*   **Outputs**:
    *   HTTP-Audio-Stream (MP3/Opus) an Clients (Browser/Player).

## 4. Abgrenzung (Out of Scope)
*   **Kein Encoding**: Der Container kodiert NICHT selbst. Das Encoding (PCM -> MP3) muss im `recorder` (ffmpeg) passieren.
*   **Keine Archivierung**: Speichert den Stream nicht auf Festplatte.
*   **Keine Analyse**: "Dummer" Relay-Server.

## 5. Technologien die dieser Container nutzt
*   **Basis-Image**: `icecast:2.4-alpine` (oder neuer)
*   **Wichtige Komponenten**:
    *   Icecast 2 Server
    *   `icecast.xml` Config

## 6. Kritische Punkte
*   **Latenz**: Icecast hat systembedingt eine Latenz von einigen Sekunden (Buffer). Für "Echtzeit"-Trigger evtl. zu langsam, aber für "Reinhören" okay.
*   **Security**: Hackme-Passwort `hackme` ist Standard in vielen Images und muss via Config/Env geändert werden.
