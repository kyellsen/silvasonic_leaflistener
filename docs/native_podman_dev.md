# Native Local Development (Fedora + Podman)

This guide describes how to run Silvasonic locally on Fedora using Podman/Compose without DevContainers.

## 1. Quick Setup

> **Audio & Sudo**: By default, the recorder needs `sudo` to access `/dev/snd`.
> **Recommendation**: For local development, avoid hardware issues by enabling Mock Mode.
> Uncomment `MOCK_HARDWARE=true` in `podman-compose.yml`.

```bash
# 1. Configure Environment (Default path: /mnt/data/dev_workspaces/silvasonic)
cp config.example.env .env

# 2. Prepare Directories & Dependencies

./setup.sh
```

## 2. Manual Directory Setup (Without setup.sh)

If you prefer to create the structure manually (e.g. on Debian/Ubuntu/Fedora), ensure these directories exist and are writable by the user running the containers (usually your user, UID 1000).

```bash
# Base Directory
export BASE_DIR=/mnt/data/dev_workspaces/silvasonic

# Create Required Directories
mkdir -p $BASE_DIR/{logs,config,status,errors,notifications}
mkdir -p $BASE_DIR/recorder/recordings
mkdir -p $BASE_DIR/uploader/config
mkdir -p $BASE_DIR/birdnet/results
mkdir -p $BASE_DIR/db/data

# Ensure Ownership (User 1000:1000)
chown -R 1000:1000 $BASE_DIR
```

## 3. Development Workflow

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
