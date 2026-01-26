# AGENTS.md

## Purpose

This file defines **all binding rules, boundaries, and expectations** for humans, agents, and automation working in the **Silvasonic** repository.

It is the **single and only AGENTS.md** in the project. All scope, responsibilities, and constraints must be derived from this document and the linked normative documentation.

---

## One-Sentence Orientation

Silvasonic is a **robust, autonomous bioacoustic monitoring device** (Raspberry Pi 5 + NVMe) designed for continuous, multi-year deployment to capture and sync soundscapes with high resilience.

## Single Source of Truth (Normative Documentation)

All product meaning lives **only** in the documentation tree below. Nothing normative may be duplicated elsewhere.

- **Architecture & Containers** → [docs/architecture/containers.md](docs/architecture/containers.md)
- **Data Flow & Storage** → [docs/architecture/data_flow.md](docs/architecture/data_flow.md)
- **Hardware & Wiring** → [docs/hardware.md](docs/hardware.md)

If behavior is not specified there, it must not be implemented.

---

## Non-Negotiable Rules for Agents and Automation

### 1. Resilience & Capture-First Discipline

Silvasonic is a recording station, not just an analytics cluster. The primary directive is **Data Capture Integrity**.

**Priority Levels:**

1.  **Recorder**: [CRITICAL] Must **never** be blocked or interrupted. It buffers in RAM and writes to NVMe.
2.  **Uploader**: [HIGH] Syncs data to the central server. Must run independently.
3.  **The HealthChecker**: [HIGH] Monitors system health and alerts on failure.
4.  **BirdNET** & **Dashboard**: [STANDARD] Supplemental. See [docs/containers.md](docs/containers.md) for full role definitions.

**Rule**: Any operation that risks the continuity of "Recorder" is forbidden.

### 2. File System & Persistence

The system uses a strict directory structure on the NVMe drive (`/mnt/data`).

**Rule**: Use only the canonical paths defined in [docs/data_flow.md](docs/architecture/data_flow.md#file-system-layout).

**Transient Scripts**:
Any temporary, investigative, or verification scripts (e.g. `verify_audio.py`) must be placed in `scripts/temp/`. They must **never** be placed in the project root.

### 3. Language Policy

- **Repository content** (code, docs, comments, commits, configs): **English only**.
- **Chat output by agents** (human explanations only): **German only**.
- Chat output is never committed.

### 4. Technical Standards

All code contributions must adhere to the following stack:

- **Python**: `>= 3.13`
- **Dependency Manager**: `uv` (Required).
- **Environment**: **Native DevContainer** (Cross-compile for Prod).
- **Linter/Formatter**: `ruff` (Google Style docstrings).
- **Type Checker**: `mypy` (Strict mode).
- **Models**: `Pydantic v2`.

**Quality Gates**:
Code is not "done" until it passes:

1. `uv run ruff check --fix`
2. `uv run mypy .`
3. `uv run pytest`

### 4. Application Constraints (Dashboard)

- **Goal**: Provides device status, statistics, and exploration tools.
- **Technology**: FastAPI.
- **Interaction**: Users may explore data (BirdDiscover) and view stats (BirdStats). Heavy analysis must be handled by the specialized containers (BirdNET), not the Dashboard itself.

---

## How to Change the System (Iterative Mode)

1.  **Check Priorities**
    - Does this change threaten "The Ear"? If yes, redesign.
2.  **files first, code second**
    - Verify paths against `setup/provision/playbooks/setup.yml`.
3.  **Implement & Verify**
    - Code must be container-aware (Podman).
    - If you change the architecture, update `docs/`.
    - **Consult `docs/DEVELOPMENT.md`** for DevContainer workflows.

---

## Commit Messages

- Commit messages must be **semantic, imperative, and in English**.
- Format: `<type>(<scope>): <summary>`
  - Examples: `feat(recorder): optimize buffer size`, `fix(healthchecker): correct email alert`.

---

## If You Are Unsure

If something is unclear or missing, you are authorized to infer a reasonable technical solution consistent with **"The Ear comes first"**.

You **must** update the corresponding specification/documentation in the same step/PR so that code and specs evolve synchronously.

**This file is the only operational authority for agents in this repository.**
