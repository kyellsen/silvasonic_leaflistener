### KONFIGURATION
ZIEL_CONTAINER="dashboard"

### AUFGABE
Du bist ein strenger **Senior Full-Stack Engineer und UX-Architekt**, der ein Audit für das Web-Interface des "Silvasonic"-Projekts durchführt.
Analysiere den Container **[ZIEL_CONTAINER]** (Ordner `containers/[ZIEL_CONTAINER]`) sowie dessen Dockerfile, Templates (`templates/`) und Statics (`static/`).

Deine Aufgabe ist es, **Schwachstellen in UI, UX und Web-Architektur gnadenlos aufzudecken**, insbesondere bzgl. Templates, Pages, Refreshes, einheitlicher UI und Konsistenz im Design. Beantworte folgende 4 Punkte:

1. **Frontend-Stack & "Modern Web" Check:**
   Das Dashboard nutzt (laut Dateistruktur) offenbar **FastAPI + Jinja2 + HTMX + Alpine.js**. 
   
   *Bewerte die Umsetzung:*
   - **"Spaghetti-Code" vs. Struktur:** Wird die Logik sauber getrennt? 
     - *Backend:* Bleibt der Router (`main.py` / `services/`) sauber, oder sickert HTML-Generierung in den Python-Code?
     - *Frontend:* Werden HTMX und Alpine.js "idiomatisch" genutzt, oder wird veraltetes jQuery-Denken (z.B. inline `onclick` Chaos) angewendet?
   - **Asset Management:** Werden CSS/JS Dateien effizient ausgeliefert? (Minification, Caching-Header? Oder lädt er riesige unkomprimierte Bilder?)
   - **Tech-Entscheidung:** Ist der Stack für ein Embedded Device angemessen? (Wäre eine Single-Page-App [React/Vue] hier Overhead, oder fehlt durch das Server-Side-Rendering die Interaktivität?)

2. **UX & Performance (The "Feel"):**
   Der User bedient dies oft mobil im Feld oder über schlechtes WLAN.
   - **Ladezeiten & Responsiveness:** Gibt es blockierende Python-Calls im Backend, die das Rendern der Seite verzögern? Werden schwere Datenbank-Queries (z.B. für Stats) asynchron geladen oder blockieren sie den Page-Load?
   - **Real-Time Feedback:** Wie werden Live-Daten (z.B. Audio-Level, Status) übertragen? (Polling vs. SSE vs. Websockets). Ist das effizient gelöst oder hämmert der Client den Server zu?
   - **Mobile First:** Wirkt der HTML/CSS-Code so, als wäre er "responsive" gebaut, oder ist es ein Desktop-Layout, das auf dem Handy kaputtgeht?

3. **Sicherheit & Isolation:**
   Ein Web-Server ist das Einfallstor Nr. 1.
   - **Auth & Input:** Wie wird der Login (`auth.py`) gehandhabt? Sind Session-Cookies sicher (HttpOnly, Secure)?
   - **Isolation:** Wenn das Dashboard crasht oder überlastet ist (z.B. durch viele Requests), reißt es dann auch kritische Background-Services (wie DB-Verbindungen für den Recorder) mit in den Abgrund?

4. **Empfohlene Handlungsoptionen (Die "Menükarte"):**
   Schlage **3 mögliche Verbesserungen** vor, priorisiert nach UX-Gewinn und Stabilität.
   Gib für jede Option an:
   - **Titel:** Kurze Bezeichnung.
   - **Das Problem:** (z.B. "Seite flackert beim Reload", "Handy-Bedienung unmöglich", "Sicherheitslücke X")
   - **Aufwand:** (Niedrig/Mittel/Hoch)
   - **Impact:** (UX/Performance/Security)
   
   *Beispiel:* *Option A: "Einführung von Server-Sent-Events (SSE) für Status" (Aufwand: Mittel, Impact: UX)*
   *Option B: "Refactoring der Jinja2-Templates in Komponenten" (Aufwand: Niedrig, Impact: Maintainability)*

### HINWEIS
Antworte auf Deutsch. Beziehe dich konkret auf Code-Stellen (z.B. in `templates/index.html` oder `main.py`). Dein Ziel ist ein professionelles, schnelles und sicheres Dashboard.