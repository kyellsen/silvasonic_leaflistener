# Silvasonic Developer Guide

> **One Workflow**: Whether Local or DevContainer, we use `uv` and `podman`.

This guide defines the engineering standards and workflows for contributing to Silvasonic.

---

## 🛠️ The Toolchain

You **must** have these tools installed on your host:

1.  **uv**: The Python package manager.
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
2.  **Podman**: The container engine.
    - **Linux**: `sudo apt install podman podman-compose`
    - **Mac**: `brew install podman podman-compose`

---

## 🚀 Development Workflow

### 1. Environment Setup

We use a single unified environment for the entire repo.

```bash
# Sync dependencies (creates .venv)
uv sync

# Activate environment
source .venv/bin/activate
```

### 2. Running Services

We run the full stack in containers, even during development, to match production.

```bash
# 1. Create Config (if not exists)
cp config.example.env .env

# 2. Start Stack
podman-compose up -d --build

# 3. View Logs
podman-compose logs -f
```

### 3. Iteration Loop

Since code is mounted into the containers (see `podman-compose.yml`), changes to Python files usually trigger a reload (if `PYTHONUNBUFFERED=1` is set and the service supports it).

For heavy changes, rebuild:

```bash
podman-compose restart <service_name>
```

---

## ✅ Quality Gates

Code is not "done" until it passes the strict quality checks.

**Run All Checks:**

```bash
./scripts/run_checks.sh
```

**Individual Tools:**

- **Lint/Format**: `uv run ruff check .`
- **Type Check**: `uv run mypy .`
- **Test**: `uv run pytest`

---

## 📂 Architecture & Persistence

We strictly separate **Code** (Immutable) from **Data** (Mutable).

| Type     | Host Location                         | Container Mount               |
| :------- | :------------------------------------ | :---------------------------- |
| **Code** | `./` (Project Root)                   | `/app/src`                    |
| **Data** | `/mnt/data/dev_workspaces/silvasonic` | `/data`, `/config`, `/status` |

> **Note**: The host data path mirrors the production structure on the Raspberry Pi (`/mnt/data/...`) to catch pathing issues early.

---

## 🐳 DevContainers

If you prefer VS Code DevContainers:

1.  Open Project in VS Code.
2.  Reopen in Container.

**Under the hood**: The DevContainer mounts the **Host's Podman Socket**. This means when you run `podman ps` inside VS Code, you are seeing the actual containers running on your host OS. This provides "Native Performance" with "Containerized Tooling".

---

## ⚡ Native / Hybrid Development

If you prefer to run Python natively on your host (e.g., for direct PyCharm/VSCode integration without DevContainers) while keeping services in containers:

👉 **See [Native Podman Guide](native_podman_dev.md)**
