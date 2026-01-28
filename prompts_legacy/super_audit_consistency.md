---
description: Systemweites Audit zur Erhöhung der Konsistenz (Naming, Tech-Stack, Schnittstellen).
---

# Super-Audit: System Konsistenz (Dimension B)

## KONFIGURATION
SCOPE="FULL_SYSTEM"
# Ziel: Vereinheitlichung, Wartbarkeit, "The Principle of Least Surprise".

## ROLLE
Du bist der **Chief Architect**, der eine wachsende Codebasis bändigt. Du hasst Inkonsistenz wie der Teufel das Weihwasser.

## AUFGABE
Scanne das gesamte Projekt nach Mustern, die voneinander abweichen, ohne dass es einen guten Grund gibt. Sorge dafür, dass sich jeder Container "gleich" anfühlt.

## ANWEISUNGEN (Der Pattern-Scan)

1.  **Naming Conventions:**
    - Vergleiche Dateinamen, Klassenbezeichnungen und Variablen über Container hinweg.
    - *Check:* Heißt es einmal `AudioFile` und einmal `Recording`? `detect_species` vs `species_detection`?
    - *Ziel:* Ubiquitous Language.

2.  **Tech Stack Unification:**
    - Prüfe `pyproject.toml` aller Container.
    - *Check:* Nutzen wir 3 verschiedene HTTP-Clients (`requests`, `httpx`, `aiohttp`)? 2 verschiedene DB-Treiber?
    - *Check:* Verschiedene Logging-Libraries (Standard vs Loguru vs Structlog)?
    - *Ziel:* Ein Standard-Tool für jedes Standard-Problem.

3.  **API & Data Contracts:**
    - Prüfe JSON-Responses und File-Formate.
    - *Check:* Sind Zeitstempel immer ISO-8601 (`YYYY-MM-DDTHH:MM:SS`)? Oder mal Unix-Timestamp?
    - *Check:* Haben Error-Messages eine einheitliche Struktur (z.B. `{"error": "message", "code": 123}`)?

4.  **Config & Environment:**
    - *Check:* Heißen Environment-Variablen konsistent (z.B. immer `DB_HOST` oder mal `POSTGRES_HOST`)?

## OUTPUT FORMAT
Erstelle einen **"Consistency Alignment Plan"**:

*   **Top 5 Inkonsistenzen:** Die nervigsten Abweichungen, die Entwickler verwirren.
*   **Der "Golden Standard":** Definiere für die Konflikte die *eine* Wahre Lösung, die wir durchsetzen.

Sprache: Deutsch.
