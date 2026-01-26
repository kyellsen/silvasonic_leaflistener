# Implementation Plan - Type Error Remediation

## Goal
Fix critical type errors identified by `scripts/run_checks.sh`, focusing on logic errors and missing type definitions in production code.

## User Review Required
> [!NOTE]
> I am prioritizing `src` files over `tests` as they affect runtime stability. I will address test files in a later pass if needed.

## Proposed Changes

### Dashboard Service
#### [MODIFY] [analysis.py](file:///workspace/containers/dashboard/src/services/analysis.py)
- Fix `Incompatible types in assignment` at line 106 (float assigned to int).
- Add missing type annotations for functions at line 12 and 110.

### Livesound Service
#### [MODIFY] [server.py](file:///workspace/containers/livesound/src/live/server.py)
- Fix `Untyped decorator` errors by ensuring decorated functions have proper type hints or suppressing false positives if necessary.
- Add missing type annotations.

## Verification Plan

### Automated Tests
- Run `uv run mypy containers/dashboard/src/services/analysis.py` to verify formatting fixes.
- Run `uv run mypy containers/livesound/src/live/server.py` to verify formatting fixes.
- Run `scripts/run_checks.sh` to see the reduced error count.
