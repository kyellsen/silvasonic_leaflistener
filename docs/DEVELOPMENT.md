# Silvasonic Development Guide

Welcome to the Silvasonic development documentation. This project uses a **Native DevContainer** approach on Fedora/Podman to ensure high performance (x86_64) while maintaining compatibility with the production Raspberry Pi environment via standard Python libraries.

## 🚀 Quick Start (DevContainer)

The recommended way to develop Silvasonic is using **VS Code DevContainers**.

### 1. Host Machine Setup (Fedora Workstation)

Since we use Podman with specific bind mounts for data persistence, you must create the storage directory on your host once. This separates your code from heavy recording data.

```bash
# Create the local data storage directory on your Host
sudo mkdir -p /mnt/data/dev_workspaces/silvasonic
sudo chown -R $USER:$USER /mnt/data/dev_workspaces/silvasonic
```

### 2. Launching the Environment

1. Open this folder in VS Code.
2. Press `F1` (or `Ctrl+Shift+P`) and select: `> Dev Containers: Reopen in Container`

The build is native and fast (running on your local architecture).

## 📂 Architecture & Data Flow

We strictly separate Code from Data to simulate the production environment and keep the Git repository clean:

| Scope | Host Path (Fedora) | Container Path | Description |
|---|---|---|---|
| Code | `./` (Project Root) | `/workspace` | Live-synced. Changes apply immediately to services. |
| Data | `/mnt/data/dev_workspaces/silvasonic` | `/mnt/data/services/silvasonic` | Persistent storage (DB, Audio). Survives container rebuilds. |

### Live Reloading

The `podman-compose.yml` mounts the source code (`./containers/*/src`) directly into the running services. If you modify a Python file, simply restart the specific service inside the DevContainer terminal to apply changes:

```bash
# Example: Restart recorder after code changes
podman-compose restart recorder
```

## 🛠️ Toolchain & Workflow

We use `uv` for high-speed dependency management inside the container.

### Dependency Management

- **Sync Environment**: `uv sync` (Restores all dependencies in `/workspace/.venv`)
- **Add Dependency**: `uv add <package>`
- **Run Scripts**: `uv run <script.py>`

### Testing

#### 1. Unit Tests

Run fast logic tests (mocked hardware):

```bash
uv run pytest
```

#### 2. Service Tests

To test specific container logic (e.g. BirdNET):

```bash
cd containers/birdnet
uv run --extra test pytest
```

### Code Quality

We enforce strict quality gates:

```bash
uv run ruff check .   # Linting
uv run ruff format .  # Formatting
uv run mypy .         # Type Checking
```

## 🐳 Podman-in-Podman

The DevContainer has access to the host's Podman socket. You can manage the "inner" production containers just like on the Raspberry Pi.

Standard Dev Stack Start:

```bash
# Inside VS Code Terminal
cp config.example.env .env
podman-compose up -d --build
```

Check Status:

```bash
podman-compose ps
```

View Logs:

```bash
podman-compose logs -f
```

Cleanup:

```bash
podman-compose down
```
