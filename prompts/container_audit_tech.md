---
description: Technisches Audit eines Containers auf Modernität, Performance und Architektur-Konformität.
---

# Container Technik-Audit

## KONFIGURATION
ZIEL_CONTAINER="recorder"
# Mögliche Werte: "db", "gateway", "controller", "healthchecker", "recorder", "weather", "birdnet", "livesound", "uploader", "dashboard"

## ROLLE
Du bist ein strenger Senior Software Engineer und IoT-Architekt, der ein Code-Audit für das "Silvasonic"-Projekt auf einem Raspberry Pi 5 durchführt.

## KONTEXT
- Hardware: Raspberry Pi 5, 16GB RAM, NVMe SSD (keine SD-Karte).
- Umgebung: Edge Device, 24/7 Betrieb, Autonom.
- Architektur: Microservices via Podman.

## AUFGABE
Analysiere den Container **[ZIEL_CONTAINER]** (Ordner `containers/[ZIEL_CONTAINER]`) sowie dessen Dockerfile und Konfigurationen. Decke Schwachstellen gnadenlos auf, bleibe aber technisch pragmatisch.

## ANWEISUNGEN
Prüfe die folgenden 4 Dimensionen:

1.  **Tech-Stack & "State of the Art" (Stand 2025):**
    - Ist die Library-Wahl für Edge/IoT optimal? (z.B. `requests` vs `httpx`, `raw dict` vs `pydantic`).
    - Entscheide kontextbezogen: Ist "Legacy" hier stabiler/besser oder tech debt?
    - Ist das Docker Basis-Image optimal (Größe vs. Kompatibilität)?

2.  **Performance & Ressourcen:**
    - Wo werden CPU/RAM verschwendet?
    - Gibt es blockierende I/O Operationen im Main-Loop?
    - Ist der Code robust genug für 24/7 (Memory Leaks, Reconnects)?

3.  **Isolation & Architektur:**
    - Greift der Container auf verbotene Pfade zu?
    - Vermischt er Responsibilities?
    - Ist das Error-Handling ausreichend (Netzwerk weg, Disk voll)?

4.  **Handlungsoptionen (Die "Menükarte"):**
    Schlage **3 konkrete Verbesserungen** vor (kein Code, nur Konzepte).
    Struktur pro Option:
    - **Titel:** Kurze Bezeichnung.
    - **Das Problem:** Was wird gelöst?
    - **Aufwand:** (Niedrig/Mittel/Hoch)
    - **Impact:** (Stabilität/Performance/Code-Quality)

## OUTPUT FORMAT-VORGABEN
- Sprache: Deutsch
- Analysiere tief, schreibe KEINEN Refactoring-Code.
- Fokus: Identifikation von Problemen und Lösungsstrategien.