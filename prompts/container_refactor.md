 ### KONFIGURATION

ZIEL_CONTAINER="recorder"

# Mögliche Werte: "controller","recorder", "birdnet", "uploader", "dashboard", "livesound", "healthchecker", "weather", "db"


### AUFGABE

Du bist ein strenger Senior Software Engineer und IoT-Architekt, der ein Code-Audit für das "Silvasonic"-Projekt auf einem Raspberry Pi 5 durchführt.

Analysiere den Container **[ZIEL_CONTAINER]** (Ordner `containers/[ZIEL_CONTAINER]`) sowie dessen Dockerfile und Konfigurationen.


Deine Aufgabe ist es, **Schwachstellen gnadenlos aufzudecken**, dabei aber **technisch pragmatisch** zu bleiben. Beantworte folgende 4 Punkte:


1. **Tech-Stack & "State of the Art" Check (mit Augenmaß):**

Verwendet dieser Container die für seine spezifische Aufgabe (Edge/IoT) sinnvollsten Bibliotheken/Tools (Stand 2025)?

*Prüfe auf Modernisierungspotenzial, aber bewerte kontextabhängig:*

- **Beispiele für mögliche Upgrades (Nur als Inspiration, kein Zwang!):**

- *HTTP:* `requests` (synchron, einfach) vs. `httpx`/`aiohttp` (asynchron, komplexer). Lohnt sich der Wechsel hier wirklich?

- *Validierung:* `raw dicts`/`argparse` vs. `pydantic`/`typer` (Typsicherheit vs. Performance-Overhead).

- *Concurrency:* `threading` vs. `asyncio`. (Ist Async hier wirklich performanter oder nur komplizierter?)

- *Serialisierung:* Standard `json` vs. High-Performance Libs wie `orjson`/`msgspec`.

- *Logging:* `print` vs. `logging` vs. `loguru`.

**Entscheidende Frage:** Ist die aktuelle Implementierung "Legacy" und ineffizient, oder ist sie "Bewährt" und genau richtig für diesen Zweck? Schlage keine "Hype-Tools" vor, wenn die aktuelle Lösung stabiler oder oder angemessener im Container Kontext erscheint.


- Ist die Wahl des Basis-Images (siehe Dockerfile) optimal (z.B. `python:slim` vs. `alpine` vs. `distroless`) in Bezug auf Größe, Build-Zeit und Kompatibilität (z.B. `musl` vs `glibc` Probleme beim Pi)?


2. **Performance & Edge-Eignung:**

Der Pi 5 hat begrenzte Ressourcen.

- Wo verschwendet dieser Container CPU-Zyklen oder RAM?

- Gibt es blockierende Operationen (I/O), die den Main-Loop aufhalten?

- Ist die Implementierung für einen 24/7-Betrieb robust genug (Memory Leaks, Caching-Strategien, Reconnect-Logik)?


3. **Verletzung von Isolation & Architektur:**

Prüfe gegen `docs/architecture/containers.md`:

- Greift der Container auf Daten oder Pfade zu, die ihn nichts angehen?

- Vermischt er Verantwortlichkeiten (z.B. macht der Recorder auch Analyse, oder der Uploader auch Datenbank-Writes, die er nicht sollte)?

- Ist das Error-Handling (z.B. bei Netzwerk-Ausfall, fehlendem Mikrofon oder voller Disk) ausreichend implementiert? 

4. **Empfohlene Handlungsoptionen (Die "Menükarte"):**
   Statt sofort Code zu schreiben, schlage **3 mögliche Verbesserungen** vor, zwischen denen ich wählen kann.
   Gib für jede Option an:
   - **Titel:** Kurze Bezeichnung.
   - **Das Problem:** Was wird gelöst?
   - **Aufwand:** (Niedrig/Mittel/Hoch)
   - **Impact:** (Stabilität/Performance/Code-Quality)
   
   *Beispiel:* *Option A: "Wechsel auf AsyncIO" (Aufwand: Hoch, Impact: Performance)*
   *Option B: "Einführung von Structlog" (Aufwand: Niedrig, Impact: Debugging)*

### HINWEIS
Antworte auf Deutsch. Analysiere tief, aber schreibe noch keinen Refactoring-Code. Ich werde im nächsten Schritt eine deiner Optionen auswählen.