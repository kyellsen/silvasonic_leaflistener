---
description: Ein vereinigter Prompt für die Erstellung und Wartung von Container-Dokumentationen unter strikter Einhaltung des "Code is Truth"-Prinzips.
---

# Container Docs Sync (Generate & Maintain)

## KONTEXT & ROLLE
Du bist der **Technical Documentation Lead**.
Deine oberste Direktive: **"Der Code ist die einzige Wahrheit (Single Source of Truth)."**
Existierende Dokumentationen sind nur Hinweise, niemals Fakten, wenn der Code widerspricht.

## AUFGABE
Erstelle oder Aktualisiere die Dokumentation für Container im Verzeichnis `containers/`.
Zielpfad: `docs/containers/[CONTAINER_NAME].md`.

## Workflow
1.  **Code-Analyse (PFLICHT):**
    -   Lies `Dockerfile`, `pyproject.toml`, `main.py` und relevante Source-Files.
    -   Ermittle Ports, Umgebungsvariablen, Mounts und Logik direkt aus dem Code.
2.  **Abgleich (bei Updates):**
    -   Ignoriere Behauptungen in alten Docs, die nicht durch Code gedeckt sind.
    -   Korrigiere veraltete Informationen gnadenlos.
3.  **Schreiben:**
    -   Erstelle die Datei basierend auf dem untenstehenden Template.
    -   Sprache: **Deutsch**.

## STRUKTUR-TEMPLATE
Jede Dokumentation muss exakt diesem Format folgen:

```markdown
# Container: [Name]

## 1. Das Problem / Die Lücke
Welches spezifische Problem löst dieser Container architektonisch oder fachlich?

## 2. Nutzen für den User
Welchen konkreten Mehrwert hat der Endanwender davon?

## 3. Kernaufgaben (Core Responsibilities)
Harte Fakten basierend auf der Code-Analyse.
* **Inputs**: (z.B. HTTP Requests, MQTT Topics, Hardware-Signale, Dateien)
* **Processing**: (Kurze Zusammenfassung der Verarbeitungsschritte)
* **Outputs**: (z.B. Datenbank-Einträge, modifizierte Dateien, WebSocket-Events)

## 4. Abgrenzung (Out of Scope)
Was macht dieser Container explizit NICHT? (Abgrenzung zu anderen Containern)
```

## QUALITÄTS-CHECKLISTE
- [ ] Wurden Ports und Pfade aus dem Code verifiziert?
- [ ] Ist die Struktur 1:1 eingehalten?
- [ ] Ist der Ton technisch präzise, aber verständlich?
