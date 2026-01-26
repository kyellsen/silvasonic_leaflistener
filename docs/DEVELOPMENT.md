# Silvasonic Development Guide

Welcome to the Silvasonic development documentation. This project uses a **Native DevContainer** approach on Fedora/Podman to ensure high performance (x86_64) while maintaining compatibility with the production Raspberry Pi environment via standard Python libraries.

## 🚀 Quick Start (DevContainer + Host)

The recommended way to develop Silvasonic is using **VS Code DevContainers** for Python logic, while managing the container infrastructure directly on your **Host Machine**.

### 1. Host Machine Prerequisites (Fedora Workstation)

Ensure you have `podman` and `podman-compose` installed on your host:

```bash
sudo dnf install podman podman-compose
```

Create the local data storage directory on your Host (separates code from data):

```bash
# Create the local data storage directory on your Host
sudo mkdir -p /mnt/data/dev_workspaces/silvasonic
sudo chown -R $USER:$USER /mnt/data/dev_workspaces/silvasonic
```

### 2. Launching the Environment

1. Open this folder in VS Code.
2. Press `F1` (or `Ctrl+Shift+P`) and select: `> Dev Containers: Reopen in Container`

This provides a managed Python environment (with `uv`, `mypy`, `ruff`) matching the production constraints.

### 3. Starting the Services (Host Terminal)

Infrastructure commands must be run from your **Host Terminal** (not inside VS Code's DevContainer terminal), as we leverage the host's native Podman for performance.

```bash
# In your project root on the Host
podman-compose up -d --build
```

Access the dashboard at **[http://localhost:8080](http://localhost:8080)**.

## 📂 Architecture & Data Flow

We strictly separate Code from Data to simulate the production environment and keep the Git repository clean:

| Scope | Host Path (Fedora) | Container Path | Description |
|---|---|---|---|
| Code | `./` (Project Root) | `/workspace` | Live-synced. Changes apply immediately to services. |
| Data | `/mnt/data/dev_workspaces/silvasonic` | `/mnt/data/services/silvasonic` | Persistent storage (DB, Audio). Survives container rebuilds. |

### Live Reloading

The `podman-compose.yml` mounts the source code (`./containers/*/src`) directly into the running services. If you modify a Python file in VS Code:

1. Save the file.
2. Restart the specific service **from your Host Terminal**:

```bash
# Host Terminal
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

## 🐳 Container Management (Host Side)

Use your local terminal (outside VS Code) to control the stack.

Standard Dev Stack Start:

```bash
# In Host Terminal
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
