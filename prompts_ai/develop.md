# Workflow: Feature Implementation & Coding
<!-- Use this prompt to GENERATE CODE. -->

## 1. Setup & Context
*   **Load Knowledge:** Read `prompts_ai/_core/context.md`.
*   **Task:** Identify the feature request (e.g., "Add Redis Auth to Controller").

## 2. Planning Phase
*   **Action:** Locate relevant files using `list_dir` and `grep_search`.
*   **Action:** Read the current state of these files with `view_file`.
*   **Constraint Check:**
    *   Does `pyproject.toml` need new dependencies?
    *   Does this break the "Rootless Podman" constraint?

## 3. Implementation Step
*   **Goal:** Write working code.
*   **Method:**
    *   Use `replace_file_content` for edits.
    *   Use `write_to_file` for new files.
*   **Style:**
    *   **Python:** Type hints (`def foo(a: int) -> str:`), Pydantic models.
    *   **Config:** Environment variables (read from `os.getenv`).

## 4. Verification Step (Immediate)
*   **Mandatory:** After writing code, VERIFY it.
    *   **Syntax:** Run `python -m py_compile [file]` (if local) or `uv run ruff check [file]`.
    *   **Tests:** If a test exists, run `uv run pytest [test_file]`.
    *   **Fix:** If verification fails, fix it IMMEDIATELY in the same turn.

## 5. Final Output
*   **Status:** "Implemented & Verified".
*   **Artifact:** Update `task.md` if present.
