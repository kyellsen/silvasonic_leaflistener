# Workflow: Documentation Sync
<!-- Use this prompt to update docs based on code. -->

## 1. Golden Rule
*   **"Code is Truth":** Never trust existing docs. Trust the code.

## 2. Process
1.  **Read Code:** `Dockerfile`, `pyproject.toml`, `main.py`.
    *   Extract: Ports, Envs, Mounts.
2.  **Read Doc:** `docs/containers/[name].md` (if exists).
3.  **Compare:**
    *   Code says Port 8000, Doc says 8080? -> **Update Doc to 8000.**
    *   Code has env `DB_HOST`, Doc misses it? -> **Add it.**
4.  **Write:** Update the markdown file.

## 3. Template (German)
Structure must follow:
*   `# Container: [Name]`
*   `## 1. Das Problem`
*   `## 2. Nutzen`
*   `## 3. Kernaufgaben` (Inputs, Processing, Outputs)
*   `## 4. Abgrenzung` (Out of Scope)
