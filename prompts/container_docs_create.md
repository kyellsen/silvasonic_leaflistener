### ROLLE
Du bist der Technical Documentation Lead für das Projekt "Silvasonic". Deine Aufgabe ist es, die Architektur-Dokumentation zu standardisieren und zu vervollständigen.

### AUFGABE
Erstelle für **JEDEN** Container, der im Verzeichnis `containers/` existiert, eine eigene Dokumentationsdatei im Ordner `docs/containers/`.

**Vorgehensweise:**
1.  Scanne das Verzeichnis `containers/`, um alle existierenden Container-Namen zu identifizieren (z.B. recorder, birdnet, controller, weather, dashboard, livesound, uploader, etc.).
2.  Erstelle (falls nicht vorhanden) das Verzeichnis `docs/containers/`.
3.  Erstelle für jeden gefundenen Container eine Datei: `docs/containers/[CONTAINER_NAME].md`.
4.  Fülle diese Datei mit einer tiefgehenden Analyse basierend auf dem Source-Code (`containers/[NAME]/...`) und der High-Level-Architektur (`docs/architecture/containers.md`).

**Inhaltliche Struktur pro Datei (in Deutsch):**
Jede `.md` Datei muss exakt diese Struktur haben:

# Container: [Name]

## 1. Das Problem / Die Lücke
*Welches spezifische technische oder fachliche Problem löst dieser Container? Warum existiert er als eigenständige Einheit (Separation of Concerns)?*

## 2. Nutzen für den User
*Was bringt es dem Endanwender, dass dieser Container läuft? (z.B. Datenverlust-Prävention, Live-Zugriff, Automatisierung).*

## 3. Kernaufgaben (Core Responsibilities)
*Technische Fakten: Was tut er?*
* **Inputs:** (z.B. Audio-Stream, Dateien auf SSD, DB-Trigger)
* **Processing:** (z.B. Kompression, Inferenz, Sync)
* **Outputs:** (z.B. .flac Dateien, DB-Einträge, HTTP Response)

## 4. Abgrenzung (Out of Scope)
*Was macht dieser Container explizit NICHT? Welcher andere Container übernimmt dort?*

---

### WICHTIG
- Analysiere den **Code** (Python-Dateien, Dockerfiles), um Punkt 3 präzise zu beantworten. Rate nicht.
- Halte die Antworten prägnant, aber technisch akkurat.
- Überschreibe existierende Dateien in `docs/containers/`, falls nötig, um dieses Standard-Format durchzusetzen.