# Silvasonic Development Guide

Welcome to the Silvasonic development documentation. This project uses a **Unified Development Workflow** powered by `uv` and `podman`. Whether you are inside a **DevContainer** or working **Locally**, the tools and commands are identical.

## 🛠️ Prerequisites

To develop Silvasonic, you **must** have the following tools installed on your host system:

1.  **uv**: Fast Python package installer and resolver.
    - Install: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2.  **Podman**: Daemonless container engine (Docker compatible).
3.  **Podman Compose**: For managing multi-container applications.

> [!IMPORTANT]
> **Why Podman locally?**
> Even for local development, we use containers to build and run the actual services (`recorder`, `birdnet`, etc.). Your local environment is primarily for running tests, linters, and managing the code.

## 🚀 Setup & Workflow

### 1. Environment Setup (Universal)

Run this once to create your virtual environment and install dependencies. This works effectively the same on your Local Host and inside the DevContainer.

```bash
# 1. Create/Sync Virtual Environment
uv sync

# 2. Activate Virtual Environment
source .venv/bin/activate
```

### 2. Dependency Management

We use `uv` exclusively. Do not use `pip` manually.

- **Add a library**: `uv add <package>` (e.g., `uv add requests`)
- **Add a dev tool**: `uv add --dev <package>` (e.g., `uv add --dev pytest`)
- **Sync after git pull**: `uv sync`

### 3. Running Services (Podman)

Start the full stack (requires `.env` file):

```bash
# 1. Create Config
cp config.example.env .env

# 2. Start System
podman-compose up -d --build

# 3. View Logs
podman-compose logs -f
```

### 4. Development & Testing

Since `uv` manages the environment, you can run tools directly if the venv is activated, or via `uv run`.

#### Code Quality (Strict Gates)

```bash
# Run all checks (Lint, Format, Types)
./scripts/run_checks.sh

# Or individually:
uv run ruff check .
uv run ruff format .
uv run mypy .
```

#### Running Tests

```bash
# Run all unit tests
uv run pytest

# Run specific service tests
uv run pytest containers/birdnet
```

## 📂 Architecture & Data Persistence

We strictly separate Code from Data.

| Scope | Host Path (Fedora/Linux)              | Container Path                  | Description                                                    |
| ----- | ------------------------------------- | ------------------------------- | -------------------------------------------------------------- |
| Code  | `./` (Project Root)                   | `/workspace`                    | Live-synced. Changes apply immediately to services on restart. |
| Data  | `/mnt/data/dev_workspaces/silvasonic` | `/mnt/data/services/silvasonic` | Persistent storage (DB, Audio). Survives container rebuilds.   |

### Setup Data Storage (Host)

You must create this directory on your host machine to ensure persistence:

```bash
sudo mkdir -p /mnt/data/dev_workspaces/silvasonic
sudo chown -R $USER:$USER /mnt/data/dev_workspaces/silvasonic
```

## 🐳 VS Code DevContainers

This project supports VS Code DevContainers for a pre-configured environment.

1.  Open folder in VS Code.
2.  `F1` -> `Dev Containers: Reopen in Container`.

The DevContainer uses the **Host's Podman Socket**. This means `podman ps` inside the DevContainer sees the containers running on your host machine.
