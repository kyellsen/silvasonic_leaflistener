# Native Local Development (Fedora + Podman)

This guide describes how to run Silvasonic locally on Fedora using Podman/Compose without DevContainers.

## 1. Quick Setup

> **Audio & Sudo**: By default, the recorder needs `sudo` to access `/dev/snd`.
> **Recommendation**: For local development, avoid hardware issues by enabling Mock Mode.
> Uncomment `MOCK_HARDWARE=true` in `podman-compose.yml`.

```bash
# 1. Configure Environment
cp config.example.env .env
# Edit .env and set SILVASONIC_DATA_DIR (e.g., /home/user/silvasonic_data)

# 2. Prepare Directories & Dependencies
./setup.sh
```

## 2. Development Workflow

### Step 1: Start Background Services

Start Postgres (auto-exposed on localhost:5432), Recorder, BirdNET, etc.

```bash
podman-compose up -d
```

### Step 2: Run Dashboard Locally

This allows hot-reloading and IDE debugging.

```bash
# one-liner to start dev server
source .venv/bin/activate && \
export $(grep -v '^#' .env | xargs) && \
export POSTGRES_HOST=localhost && \
uvicorn containers.dashboard.src.main:app --reload --port 8080 --app-dir .
```

Access Dashboard: [http://localhost:8080](http://localhost:8080)
