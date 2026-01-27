### KONFIGURATION
ZIEL_CONTAINER="recorder"  
# Mögliche Werte: "controller","recorder", "birdnet", "uploader", "dashboard", "livesound", "healthchecker", "weather", "db"
GEWAEHLTE_AUFGABE="[HIER EINFÜGEN WAS DU MACHEN WILLST, Z.B. 'Option B: Einführung von Structlog']"

### ROLLE
Du bist Lead Developer im Silvasonic-Projekt. Wir haben uns entschieden, für den Container **[ZIEL_CONTAINER]** die Aufgabe **"[GEWAEHLTE_AUFGABE]"** umzusetzen.

### AUFGABE
Erstelle einen detaillierten, schrittweisen **Implementierungsplan** (Implementation Guide), um diese Änderung sicher durchzuführen.

**Struktur des Plans:**

1. **Vorbereitung & Dependencies:**
   - Müssen Librarie in `pyproject.toml` hinzugefügt oder entfernt werden?
   - Muss das `Dockerfile` angepasst werden?

2. **Code- und Architektur-Änderungen (Schritt für Schritt)**

3. **Risiko-Minimierung & Tests:**

Anmerkung: Legacy Nie einführen, direkt entfernen - wir sind in der MVP Phase des Projektes. Migrationsschritte nicht planen - ich lade einfach komplette Umgebung und container neu!

### AUSGABE
- Implementierungsplan
