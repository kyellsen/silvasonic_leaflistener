# Workflow: System Audit & Analysis
<!-- Use this prompt to perform deep audits of the codebase. -->

## 1. Setup & Context
*   **Load Knowledge:** First, read `prompts_ai/_core/context.md` and `prompts_ai/_core/tools.md`.
*   **User Intent:** Ask the user (or infer) the **Audit Dimension**:
    *   `TECH`: Modernity, Performance, Cleanup.
    *   `LEAN`: Bloat analysis, "Value Check", Overengineering.
    *   `SEC`: Security, IAM, Permissions.

## 2. Execution Steps (Agentic)

### Step 2.1: Discovery
*   **Action:** Run `list_dir` on `containers/` to see the landscape.
*   **Action:** For the target container (if specified), read `pyproject.toml` and `Dockerfile`.

### Step 2.2: The Audit Logic (Choose one based on Dimension)

#### Dimension: TECH (Modernity)
*   **Goal:** Find legacy patterns.
*   **Tools:**
    *   `grep_search(Query="requirements.txt", SearchPath=".")` -> Should be `pyproject.toml`.
    *   `grep_search(Query="os.system", SearchPath=".")` -> Should be `subprocess`.
*   **Output:** List technical debt and upgrade paths.

#### Dimension: LEAN (Value Check)
*   **Goal:** Identify High-Complexity vs. Low-Value code.
*   **Logic:**
    *   **Microservices:** Does the separation of `controller` vs `recorder` add resilience (Good) or just network overhead (Bad)?
    *   **Tech Stack:** Does `HTMX/Tailwind` make us faster (Good) or require endless config (Bad)?
    *   **Abstractions:** Search for Base Classes with only ONE implementation (`grep_search(Query="class Base", ...)`).
*   **Output:** Create a "Sustainability Report" (High-Value Complexity vs. Maintenance Traps).

#### Dimension: SEC (Security)
*   **Goal:** Hardening.
*   **Tools:**
    *   `grep_search(Query="password", SearchPath=".")` -> Hardcoded secrets?
    *   `grep_search(Query="root", SearchPath="Dockerfile")` -> Running as root?
*   **Output:** Security Risk Assessment.

## 3. Reporting
*   **Format:** Markdown File `audit_report_[DIMENSION].md`.
*   **Style:** German, Critical but Constructive.
