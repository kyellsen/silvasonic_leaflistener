# Container: silvasonic_recorder

## 1. Das Problem / Die Lücke
Wir benötigen eine extrem stabile Audio-Aufnahme, die auch bei hoher Systemlast nicht abbricht ("Glitch-Free"). Gleichzeitig brauchen wir verschiedene Formate (High-Res für Fledermäuse, Low-Res für Vögel/Web), wollen aber nicht mehrfach vom selben USB-Gerät lesen (was oft technisch unmöglich ist).

## 2. Nutzen für den User
*   **Zuverlässigkeit**: Dedizierter Prozess nur für Audio.
*   **Dual-Stream**: Gleichzeitige Aufnahme von Ultraschall (Bat-Detektor) und hörbarem Audio (Vogelstimmen/Live-Stream) aus einer Quelle.
*   **Effizienz**: Nutzt `ffmpeg`, um Sample-Rates on-the-fly zu konvertieren, ohne viel CPU für unnötige Encodierung (Archivierung in WAV) zu verschwenden.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs**:
    *   **ALSA Audio Stream**: Rohdaten vom USB-Mikrofon.
    *   **Environment Config**: Audio-Profil (Rate, Gain) vom Controller injiziert.
*   **Processing**:
    *   **FFmpeg Complex Filter**: Splittet das Signal.
        *   Stream 1: Pass-Through (z.B. 384kHz) -> Segmentierung.
        *   Stream 2: Resample (48kHz) -> Segmentierung.
        *   Stream 3: Resample (48kHz) -> MP3 Encoding -> Icecast Stream.
*   **Outputs**:
    *   **Dateien**: `.wav` Chunks (z.B. alle 10s) in `/data/recordings/{id}/high_res` und `low_res`.
    *   **Stream**: TCP-Stream an den `silvasonic_livesound` Container.
    *   **Redis Heartbeat**: Status-Updates.

## 4. Abgrenzung (Out of Scope)
*   **Kein Upload**: Lädt nichts in die Cloud.
*   **Keine Analyse**: Führt keine Fledermaus- oder Vogelerkennung durch.
*   **Kein Indexing**: Schreibt nur Dateien, trägt sie nicht in die Datenbank ein.

## 5. Technologien die dieser Container nutzt
*   **Basis-Image**: Python 3.11+ (mit installiertem `ffmpeg`).
*   **Wichtige Komponenten**:
    *   `ffmpeg` (Das Herzstück)
    *   `alsa-utils`
    *   Python Subprocess Wrapper (zur Steuerung)
    *   `redis` (Status)

## 6. Kritische Punkte
*   **Template-Natur**: Dieser Container wird selten "direkt" via Compose gestartet, sondern meist als Template benutzt, von dem der Controller Instanzen ableitet (`silvasonic_recorder_[id]`).
*   **SD-Karten Verschleiß**: Schreibt permanent WAV-Dateien. Ein NVMe-Drive oder gute "Industrial" SD-Karte ist Pflicht.
*   **CPU Priority**: Sollte im Konzept eine hohe Priorität haben. Wenn ffmpeg stockt, ist die Aufnahme ruiniert.
