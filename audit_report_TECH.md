# System Audit: Dimension TECH (Modernisierung)

**Datum:** 2026-01-28
**Scope:** Alle Container
**Dimension:** TECH (Modernity, Performance, Cleanup)

## 1. Zusammenfassung (Management Summary)
Das System befindet sich technisch auf einem **sehr hohen Modernisierungsgrad**. Legacy-Altlasten wurden aggressiv entfernt. Die Nutzung von `uv` und `pyproject.toml` ist weitgehend standardisiert.
*   **Legacy Code Index:** 0/10 (Perfekt - Keine `os.system` oder `requirements.txt` Abhängigkeiten im Code).
*   **Standardisierungs-Index:** 7/10 (Gut - `uv.lock` fehlt in einigen Containern).

## 2. Detail-Analyse

### 2.1 ✅ Erfolg: Keine Legacy-Execution Patterns
Es wurden **0 Instanzen** von `os.system` oder unsicheren `subprocess` Calls (`shell=True`) gefunden. Das System nutzt durchgängig moderne, sichere Aufrufe.

### 2.2 ✅ Erfolg: Pyproject.toml Standard
Alle Python-basierten Microservices nutzen `pyproject.toml` als Single Source of Truth für Abhängigkeiten:
*   `birdnet`, `controller`, `dashboard`, `healthchecker`, `livesound`, `recorder`, `uploader`, `weather`.
*   *Hinweis:* `db` und `gateway` nutzen zurecht keine Python-Paketierung (Standard Images).

### 2.3 ⚠️ Uneinheitlichkeit: Lockfiles
Während `pyproject.toml` überall existiert, ist die **Lockfile-Abdeckung inkonsistent**. `uv.lock` garantiert deterministische Builds, fehlt aber in 50% der Services.

| Container | Status | Handlung erforderlich? |
| :--- | :--- | :--- |
| `birdnet` | ✅ `uv.lock` vorhanden | Nein |
| `dashboard` | ✅ `uv.lock` vorhanden | Nein |
| `recorder` | ✅ `uv.lock` vorhanden | Nein |
| `uploader` | ✅ `uv.lock` vorhanden | Nein |
| `controller` | ❌ **Kein Lockfile** | **Ja** (`uv sync`) |
| `healthchecker` | ❌ **Kein Lockfile** | **Ja** (`uv sync`) |
| `livesound` | ❌ **Kein Lockfile** | **Ja** (`uv sync`) |
| `weather` | ❌ **Legacy Artefakt** | **Ja** (`requirements.txt` löschen, `uv sync`) |

## 3. Handlungsempfehlungen (Action Plan)

### Priorität 1: Standardisierung abschließen
Führen Sie folgende Commands aus, um die Builds deterministisch zu machen:

```bash
# 1. Weather bereinigen
rm containers/weather/requirements.txt

# 2. Lockfiles generieren
cd containers/controller && uv sync
cd ../healthchecker && uv sync
cd ../livesound && uv sync
cd ../weather && uv sync
```

### Priorität 2: CI/CD Härtung
Stellen Sie sicher, dass die Deployment-Pipeline explizit `uv run` oder `uv sync --frozen` verwendet, um die Nutzung der Lockfiles zu erzwingen.
