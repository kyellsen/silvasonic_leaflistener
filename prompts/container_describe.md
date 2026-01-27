### KONFIGURATION
ZIEL_CONTAINER="recorder"  
# Mögliche Werte: "recorder", "birdnet", "uploader", "dashboard", "livesound", "healthchecker"

### AUFGABE
Du bist ein erfahrener Software-Architekt, der das "Silvasonic"-Projekt analysiert. Deine Aufgabe ist es, den oben definierten ZIEL_CONTAINER basierend auf der vorliegenden Codebasis und Dokumentation (insbesondere `docs/`, `README.md` und dem Ordner `containers/[ZIEL_CONTAINER]`) tiefgehend zu untersuchen.

Bitte beantworte die folgenden vier Punkte prägnant und verständlich für den oben genannten Container:

1. **Das konkrete Problem / Die Lücke:**
   Welches spezifische technische oder fachliche Problem löst dieser Container? Warum existiert er als eigenständige Einheit und ist nicht Teil eines anderen Containers? (Beziehe dich auf die "Why separate?" Logik in der Doku).

2. **Nutzen für den Silvasonic-User:**
   Was bringt es dem Endanwender, dass dieser Container läuft? Welches Feature oder welche Datensicherheit garantiert er?

3. **Kernaufgaben (Core Responsibilities):**
   Was tut der Container technisch ganz konkret? (z.B. Inputs, Verarbeitung, Outputs, verwendete Schnittstellen oder Protokolle).

4. **Abgrenzung (Was ist NICHT seine Aufgabe):**
   Was macht dieser Container explizit nicht? Wo endet seine Zuständigkeit und welcher andere Container übernimmt dort?

### HINWEIS
Antworte auf Deutsch. Nutze Fachbegriffe korrekt, aber erkläre den Nutzen so, dass er intuitiv verständlich ist.