# Fix Mypy Errors

The goal is to resolve the 183 mypy errors reported in the codebase. Most errors are due to missing type annotations in test files and some source files.

## Proposed Changes

### Tools
#### [MODIFY] [mock_stream.py](file:///workspace/tools/mock_stream.py)
- Add return type annotations to functions.
- Fix untyped calls.

### Birdnet Container
#### [MODIFY] [database.py](file:///workspace/containers/birdnet/src/database.py)
- Fix recursive type alias or untyped call issues.

#### [MODIFY] [test_clip_saving.py](file:///workspace/containers/birdnet/test_clip_saving.py)
- Add `-> None` to test functions.
- Fix argument type mismatches.

### Uploader Container
#### [MODIFY] [test_rclone.py](file:///workspace/containers/uploader/tests/test_rclone.py)
- Add `-> None` to test functions.

#### [MODIFY] [test_main.py](file:///workspace/containers/uploader/tests/test_main.py)
- Add `-> None` to test functions.

#### [MODIFY] [test_janitor.py](file:///workspace/containers/uploader/tests/test_janitor.py)
- Add `-> None` to test functions.
- Add type hints for variables.

#### [MODIFY] [test_database.py](file:///workspace/containers/uploader/tests/test_database.py)
- Add `-> None` to test functions.
- Fix module loader type issues.

#### [MODIFY] [conftest.py](file:///workspace/containers/uploader/tests/conftest.py)
- Add return types to fixtures.

### E2E Tests
#### [MODIFY] [test_dashboard.py](file:///workspace/tests/e2e/test_dashboard.py)
- Add `-> None` to test functions.

## Verification Plan

### Automated Tests
- Run `uv run mypy .` to verify all type errors are resolved.
- Run `scripts/run_checks.sh` to ensure all checks pass.
