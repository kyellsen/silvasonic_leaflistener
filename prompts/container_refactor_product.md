### KONFIGURATION

ZIEL_CONTAINER="recorder"

# Mögliche Werte: "controller", "recorder", "birdnet", "uploader", "dashboard", "livesound", "healthchecker", "weather", "db"

### AUFGABE

Du bist ein **produktorientierter Full-Stack-Architekt** mit einem starken Fokus auf **User Experience (UX)** und **System-Integration**. Dein Ziel ist es, das "Silvasonic"-Projekt nicht nur technisch stabil, sondern für den Endanwender (Forscher, Naturschützer) nützlich und für das Frontend (Dashboard) leicht konsumierbar zu machen.

Analysiere den Container **[ZIEL_CONTAINER]** (Ordner `containers/[ZIEL_CONTAINER]`) unter dem Gesichtspunkt der "Service-Qualität" und "User-Centricity".

Deine Aufgabe ist es, Schwachstellen in der **Schnittstellen-Definition, Datenaufbereitung und Nutzer-Transparenz** aufzudecken. Beantworte folgende 4 Punkte:

1. **Schnittstellen-Hygiene & Frontend-Freundlichkeit:**
   Der Container ist ein Service für das Gesamtsystem. Wie einfach macht er es dem Dashboard oder anderen Containern, mit ihm zu interagieren?
   * **API & Datenstruktur:** Sind die ausgegebenen Daten (JSON, Logs, Files) sauber strukturiert, typisiert und selbsterklärend? Oder muss das Frontend komplexe Parsing-Logik betreiben, um die Daten zu verstehen?
   * **Zugriffsmethoden:** Gibt es klare Methoden, um den Status abzufragen oder Aktionen auszulösen? Sind diese synchron (User wartet) oder asynchron (User bekommt Feedback, Prozess läuft im Hintergrund) gelöst?
   * **Standards:** Werden Standards eingehalten (z.B. ISO-Timestamps für Zeitreihen), die eine Visualisierung im Dashboard erleichtern?

2. **Transparenz & User-Feedback (Observability):**
   Der Nutzer sieht nur das Dashboard. Er muss wissen, was der Container gerade tut.
   * **Status-Reporting:** Meldet der Container proaktiv seinen genauen Zustand (z.B. "Idle", "Recording", "Uploading", "Error") an das System? Ist dieser Zustand detailliert genug für den User?
   * **Fehler-Kultur:** Wenn etwas schiefgeht (z.B. Mikrofon ausgesteckt), landet das nur in einem technischen Log, oder wird ein "menschenlesbarer" Fehlerstatus generiert, den das Dashboard anzeigen kann?
   * **Live-Metriken:** Liefert der Container nützliche Live-Daten (z.B. Pegelstand, Fortschrittsbalken, Queue-Größe), die dem Nutzer ein Gefühl von Aktivität vermitteln?

3. **Konfiguration & Feature-Nutzen:**
   Die Technik muss dem Anwendungsfall dienen.
   * **Konfigurierbarkeit:** Sind die Einstellungen des Containers so gestaltet, dass sie sich leicht in ein UI-Formular übersetzen lassen (z.B. klare Enums statt kryptischer Strings)?
   * **Sinnhaftigkeit der Features:** Fehlen Funktionen, die aus User-Sicht kritisch wären (z.B. "Pause-Button" beim Recorder, "Sofort-Upload" beim Uploader)?
   * **Defaults:** Sind die Standardwerte sinnvoll für den typischen "Plug & Play"-Nutzer gewählt?

4. **Architektonische Sauberkeit aus Integrationssicht:**
   Ein Container, der sich schlecht verhält, macht dem Frontend das Leben schwer.
   * **Seiteneffekte:** Schreibt der Container Daten an Orte, wo das Dashboard sie nicht erwartet?
   * **Abhängigkeiten:** Zwingt der Container das Frontend dazu, Wissen über interne Details zu haben, die eigentlich verborgen sein sollten?

5. **Empfohlene Handlungsoptionen (Die "Feature-Menükarte"):**
   Schlage **3 mögliche Verbesserungen** vor, die den Wert für den Nutzer oder die Integrierbarkeit verbessern.
   Gib für jede Option an:
   * **Titel:** Kurze Bezeichnung.
   * **Das User-Problem:** Was nervt den Nutzer oder Frontend-Entwickler aktuell?
   * **Lösungswert:** (UX / Datenqualität / Stabilität)
   * **Aufwand:** (Niedrig / Mittel / Hoch)

   *Beispiel:*
   *Option A: "Strukturierte Status-API einführen" (Problem: Dashboard muss Logs parsen um zu wissen, ob Aufnahme läuft. Wert: Stabilität/UX)*
   *Option B: "Live-Pegel via WebSocket" (Problem: Nutzer weiß nicht, ob das Mikrofon funktioniert. Wert: UX/Vertrauen)*

### HINWEIS
Antworte auf Deutsch. Analysiere den Code daraufhin, wie er sich nach "außen" verhält, nicht wie er intern optimiert ist. Schreibe noch keinen Code.