# Workflow: Verification & Testing
<!-- Use this prompt to create tests or run verification suites. -->

## 1. Setup
*   **Context:** `prompts_ai/_core/context.md`.
*   **Target:** Which component needs verification?

## 2. Strategy
*   **Unit Tests:**
    *   Use `pytest`.
    *   Mock external dependencies (Redis, Hardware) using `unittest.mock`.
    *   Path: `tests/` inside the container folder.
*   **Integration Tests:**
    *   Use `testcontainers` if needed, or simple script-based E2E.

## 3. Execution
*   **Action:** Create/Edit test file `test_[name].py`.
*   **Action:** Run `uv run pytest test_[name].py`.
*   **Loop:** Read Output -> Fix Code -> Retry.

## 4. Report
*   **Success:** "All tests passed."
*   **Failure:** "Tests failed with error X. Analysis: Y."
