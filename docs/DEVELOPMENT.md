# Silvasonic Development Guide

Welcome to the Silvasonic development documentation. This project uses a **Container-First** approach with strict parity between Development (x86_64 Workstations) and Production (ARM64 Raspberry Pi 5).

## 🚀 Quick Start (DevContainer)

The recommended way to develop Silvasonic is using **VS Code DevContainers**. This guarantees that your environment (Python 3.11, default audio libraries, system tools) matches the target Raspberry Pi exactly, running via QEMU emulation.

### 1. Host Machine Setup (One-Time)

The DevContainer runs an **ARM64** image. To run this on a standard Intel/AMD Laptop (Fedora/Ubuntu), you must enable QEMU hardware emulation.

#### Fedora / RHEL

```bash
# Install QEMU user static emulation
sudo dnf install qemu-user-static

# Register ARM binaries with the kernel
# (The easiest way is via this multiarch container)
sudo podman run --rm --privileged multiarch/qemu-user-static --reset -p yes
```

#### Ubuntu / Debian

```bash
sudo apt-get install qemu-user-static
sudo docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
```

### 2. Launching the Environment

1. Open this folder in VS Code.
2. Press `F1` (or `Ctrl+Shift+P`) and select:
   **> Dev Containers: Reopen in Container**
3. Wait for the build to complete (Initial build may take 5-10 minutes as it emulates ARM builds).

---

## 🛠️ Toolchain & Workflow

Inside the DevContainer, you have access to the exact set of tools used in production.

### Dependency Management (`uv`)

We do not use `pip` directly. We use [uv](https://github.com/astral-sh/uv).

- **Sync Environment**: `uv sync` (Restores all dependencies)
- **Add Dependency**: `uv add <package>` (root) or `cd containers/xyz && uv add <package>`
- **Run Scripts**: `uv run <script.py>`

### Testing

Tests are split into two categories:

#### 1. Unit Tests (Fast, Mocked)

Run these from the repo root. They test logic without heavy external dependencies.

```bash
uv run pytest
```

_Note: Some containers (like `birdnet`) are excluded from root collection if they have conflicting heavy dependencies. Run their tests specifically:_

#### 2. Container Integration Tests

To test heavy components (BirdNET, Recorder) specifically:

```bash
cd containers/birdnet
uv run --extra test pytest
```

### Code Quality

We enforce strict linting and typing.

```bash
# Run Linter
uv run ruff check .

# Run Formatter
uv run ruff format .

# Type Checking
uv run mypy .
```

---

## 🏗️ Architecture Notes for Contributors

### Root vs. Containers

- **Root**: Contains shared tooling, docs, and orchestration logic (`podman-compose.yml`).
- **`containers/`**: Independent microservices. Each is a valid Python package with its own `pyproject.toml`.

### Hardware Mocking

The DevContainer puts you in an environment where standard Linux audio tools (`sox`, `ffmpeg`, `arecord`) are present.

- **Audio**: You are in the `audio` group. ALSA devices may be emulated or passed through depending on host config.
- **GPIO**: Mocked or unavailable. Use `tools/mock_gpio.py` (if available) for sensor logic testing.

### Podman

You can build and run system containers _inside_ the DevContainer (Nested Containers), thanks to the installed `podman` CLI.

```bash
# Build the production 'ear' container inside your dev environment
podman build -t silvasonic-ear ./containers/recorder
```
