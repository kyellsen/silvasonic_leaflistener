# Silvasonic System Context
<!-- This file acts as the Single Source of Truth for Project Facts. -->

## 1. Environment & Hardware
*   **Device:** Raspberry Pi 5 (8GB RAM).
*   **Storage:** NVMe SSD (No SD Card).
*   **OS:** Linux (Debian/Raspbian).
*   **Connectivity:** WiFi, no wired Ethernet usually.
*   **Users:** Field scientists/biologists (Non-technical).

## 2. Tech Stack
*   **Container Runtime:** Podman (Rootless, via `podman-compose`).
*   **Language:** Python 3.11+.
*   **Dependencies:** Management via `uv` (faster `pip` replacement).
*   **Config:** `pyproject.toml` is the authority for dependencies.
*   **Web Framework:** FastAPI (implied by usage in Controller/Dashboard).
*   **Inter-Service:** HTTP APIs, shared Redis (for status), NO shared files for status interaction.

## 3. Architecture Principles
*   **"Code is Truth":** Docs are secondary. If code differs, code wins.
*   **Microservices:**
    *   `controller`: Orchestrates hardware, manages lifecycle.
    *   `dashboard`: UI for users (HTMX, Tailwind).
    *   `recorder`: Audio capture (PyAudio/Alsa).
    *   `upload`: Data sync to cloud.
    *   `weather`, `birdnet`, `livesound`: Specialized functional containers.
*   **Persistence:** `db` container (Postgres/SQLite) + Redis.

## 4. Development Constraints
*   **No "Magic" Abstractions:** Prefer explicit Python code over complex frameworks.
*   **Value over Pure Code:** Features must serve the user (Biologist), not just be "clean code".
*   **Environment Aware:** Code must handle DEV vs PROD (Hardware availability).
