# Agent Tool Usage Guidelines
<!-- Instructions on how to effectively use tools in this project. -->

## 1. Discovery First
*   **Initial Scan:** Always run `list_dir` on the target directory before making assumptions.
*   **Deep Search:** Use `grep_search` to find usage patterns (e.g., `grep_search(SearchPath=".", Query="BaseRecorder")`).

## 2. Reading Files
*   **Context:** Read `pyproject.toml` to understand available libraries.
*   **Source:** Read `main.py` to understand the entry point.
*   **Efficiency:** Use `view_file` on specific files rather than reading entire directories blindly.

## 3. Modification (Coding)
*   **Atomic Writes:** When writing code, write the FULL file content if small, or use `replace_file_content` for surgical edits.
*   **Safety:** Always check if a file exists before overwriting, unless intent is creation.

## 4. Verification
*   **Linting:** After editing python files, run: `uv run ruff check path/to/file` (if available) or check for syntax errors.
*   **Testing:** If `tests/` exist, run `uv run pytest path/to/test`.
