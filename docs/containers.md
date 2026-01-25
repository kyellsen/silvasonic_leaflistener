# Container Architecture

The Silvasonic architecture is designed around resiliency. The system is split into four logical blocks, each isolated in its own container to ensure that critical functions (recording) are not affected by secondary tasks (UI, Uploads).

## 1. The Recorder

**Role:** Critical Audio Capture
**Status:** Privileged / Real-time priority

- **Function**: Captures audio directly from the Dodotronic Ultramic384 EVO via ALSA/SoundDevice.
- **Operation**:
  - buffers audio in RAM to avoid dropped samples.
  - Writes compressed **.flac** files to the NVMe SSD (`/mnt/data/services/silvasonic/recorder/recordings`).
- **Why separate?**: This container is "sacred". It must never crash or be stopped, even if the dashboard fails or the network hangs.

## 2. The Uploader

**Role:** Data Sync & Transport
**Status:** Low priority background process

- **Function**: Synchronizes recorded files to the central server.
- **Technology**: Syncthing or Rclone (wrapped in a script).
- **Mounts**: Mounts the storage directory as **Read-Only** to prevent accidental deletion or corruption by the sync process.
- **Why separate?**: Network operations can be resource-intensive or hang. Isolating this ensures that a stuck upload doesn't block the recording loop.

## 3. The SoundAnalyser (Optional)

**Role:** Edge Inference
**Status:** Standard priority

- **Function**: Watches for new files and processes them through on-device ML models (e.g., Bat detectors).
- **Output**: Writes results to a lightweight database (DuckDB/SQLite) or JSON sidecar files.
- **Why separate?**: ML libraries (TensorFlow, PyTorch) are heavy and can be unstable. Updates to the model should not risk the stability of the core recorder.

## 4. The Face (Dashboard)

**Role:** Local Status & Diagnostics
**Status:** Standard priority

- **Function**: User interface for checking the device status locally.
- **Tech Stack**: FastAPI + HTMX or Streamlit.
- **Features**:
  - "Last recording 2s ago"
  - "SSD 40% full"
  - "50 Bats detected (approx)"
- **Note**: Admin-level system management (restart, logs, updates) is handled by **Cockpit** running on the host, not this container.

## 5. The Notifier (Watchdog)

**Role:** Monitoring & Alerts
**Status:** High Availability / Watchdog

- **Function**: Monitors the health of other containers and sends alerts.
- **Dead Man's Switch**: Monitors the Uploader status. If no successful upload occurs for >60 minutes, triggers an email via SMTP.
- **Critical Error Relay**: Watches the shared `/errors` directory for crash dumps from any service and emails them immediately.
- **Why separate?**: Monitoring must be independent of the monitored services. If the Uploader freezes, the Notifier (running in its own isolated process) remains alive to sound the alarm.
