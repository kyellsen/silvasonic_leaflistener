# Code Audit: Recorder Container

## 1. Tech-Stack & "State of the Art" Check

*   **Basis-Image:** `python:3.11-slim-bookworm` ist eine exzellente Wahl (stabil, sicher, klein, aktuelle Python-Version).
*   **Dependency Management:** Die Nutzung von `uv` ist absolut "State of the Art" (extrem schnell, deterministisch).
*   **Libraries:**
    *   `numpy` und `soundfile` sind Standard für Audio.
    *   `ffmpeg` (via Subprocess) ist der Industriestandard für robuste Audio-Pipeline-Arbeit.
    *   **Fehlend:** `pydantic`! Der Container nutzt `dataclasses` und lädt YAML/JSON manuell. Im Jahr 2025 ist `pydantic` für Typsicherheit und Validierung bei IoT-Configs quasi Pflicht. `pyproject.toml` listet es nicht.
    *   **Code-Stil:** Typ-Hints sind vorhanden, aber teilweise generisch (`typing.Any`).

## 2. Performance & Edge-Eignung

*   **CPU:** Sehr effizient. Die Hauptlast (Encoding) liegt bei `ffmpeg` (C-Level). Python macht nur Management.
*   **RAM:** `numpy` wird nur lazy importiert (in `strategies.py`), was RAM spart, wenn man keinen Mock-Modus nutzt. Gut!
*   **IO / Disk-Wear:**
    *   ⚠️ **Risiko:** Die Funktion `write_status` schreibt alle 5 Sekunden (oder sogar schneller) eine JSON-Datei auf die Festplatte (`/mnt/data/services/silvasonic/status`). Auf einem Raspberry Pi mit SD-Karte kann das langfristig die Karte zerstören (Write Amplification).
    *   **Lösung:** Status nur schreiben, wenn er sich ändert, oder in `tmpfs` (RAM-Disk) schreiben.
*   **Robustheit:**
    *   Gute Exception-Handling im Main-Loop. Restart-Logik (5s Delay) ist vorhanden.
    *   `consume_stderr` Thread verhindert Buffer-Overlow.

## 3. Verletzung von Isolation & Architektur

*   **Verantwortlichkeiten:** Der Container hält sich gut an seine Aufgabe (Audio-Akquise). Keine unerlaubte Analyse oder Cloud-Uploads.
*   **Hardware-Zugriff:** Er greift direkt auf ALSA zu (`/dev/snd`). Das ist notwendig, aber die autark durchgeführte Hardware-Erkennung (`arecord -l` Parsing in `mic_profiles.py`) dupliziert teilweise Logik, die der Controller eigentlich zentral verwalten sollte. Trotzdem erhöht es die Autonomie des Containers positiv.
*   **Error Handling:** Solide. Wenn das Mikrofon weg ist, stirbt der Prozess und wird restartet. Das ist für Docker/Systemd Supervisor-Patterns okay.

## 4. Konkreter Refactoring-Plan

1.  **Einführung von Pydantic:**
    *   Ersetze das manuelle Parsing in `mic_profiles.py` durch Pydantic-Models (`BaseModel`).
    *   Das garantiert, dass ungültige YAML-Configs sofort crashen (Fail Fast) und verhindert subtile Bugs durch falsche Typen.

2.  **Status-IO Optimieren (Wichtig für Edge!):**
    *   Ändere `write_status` so, dass es (a) prüft, ob sich der Status wirklich geändert hat, bevor es schreibt, oder (b) die Frequenz reduziert (z.B. nur alle 30s Heartbeat).
    *   Alternativ: Konfiguriere `STATUS_DIR` explizit als `tmpfs` Volume im Docker-Compose/Podman.

3.  **Migration auf AsyncIO:**
    *   Ersetze das Threading (`consume_stderr`) und `subprocess.Popen` durch `asyncio` und `asyncio.create_subprocess_exec`.
    *   Das macht das Signal-Handling (SIGTERM) sauberer und erlaubt später einfache Erweiterungen (z.B. einen kleinen HTTP-Health-Endpoint), ohne in die "Thread-Hölle" zu geraten.
