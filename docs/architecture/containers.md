# Container Architecture

The Silvasonic architecture is designed as a **Producer-Consumer pipeline** centered around the filesystem.

1. **Producer**: The **Recorder** captures live audio and writes files to the SSD.
2. **Consumers**: The **BirdNET** (Analyzer) and **Uploader** independently watch the filesystem to process these files.

This ensures that critical recording is never blocked by analysis or network speeds.

## Data Flow

`Ultramic` -> **Recorder** -> `[SSD Storage]` -> **BirdNET** (Analysis)
-> **Uploader** (Cloud Sync)
-> **Dashboard** (Playback)

## 1. Recorder

**Role:** Critical Audio Capture
**Status:** Privileged / Real-time priority

- **Function**: Captures audio directly from the Dodotronic Ultramic384 EVO via ALSA/SoundDevice.
- **Operation**:
  - Buffers audio in RAM to avoid dropped samples.
  - Writes compressed **.flac** files to the NVMe SSD (`/mnt/data/services/silvasonic/recorder/recordings`).
- **Why separate?**: This container is "sacred". It must never crash or be stopped, even if the dashboard fails or the network hangs.

## 2. Uploader

**Role:** Data Sync & Transport
**Status:** Low priority background process

- **Function**: Synchronizes recorded files to the central server (Nextcloud/WebDAV or Rsync).
- **Technology**: Custom Python wrapper (`uploader` container) handling sync logic via `rclone`.
- **Mounts**: Mounts the storage directory with managed access to prevent accidental deletion or corruption by the sync process.
- **Why separate?**: Network operations can be resource-intensive or hang. Isolating this ensures that a stuck upload doesn't block the recording loop.

## 3. Livesound (formerly SoundAnalyser)

**Role:** Specialized Analysis & Live Streaming
**Status:** Standard priority

- **Function**: Framework for live streaming audio and running custom acoustic analysis.
- **Config**: Exposes port 8000 for live stream access.

## 4. BirdNET

**Role:** Species Classification
**Status:** Standard priority

- **Function**: Analyzes audio files to detect and classify bird species using the BirdNET model.
- **Operation**:
  - Watches for new recordings.
  - Processes audio segments to generate detection entries.
  - Stores results in the internal database.
- **Why separate?**: Inference is CPU/RAM heavy. It must run decoupled from the recording loop.

## 5. Weather (Disabled)

**Role:** Environmental Monitoring
**Status:** Disabled in default config.

## 6. Database (PostgreSQL)

**Role:** Central Storage
**Status:** Service

- **Function**: PostgreSQL database storing detection results and structured data for the Dashboard and analysis tools.

## 7. HealthChecker

**Role:** Monitoring & Alerts
**Status:** High Availability / Watchdog

- **Function**: Monitors the health of other containers and system resources.
- **Features**:
  - **Service Checks**: Verifies that Recorder, Uploader, etc., are running and responsive.
  - **Log Rotation**: Manages log sizes.
  - **Alerting**: Sends notifications on critical failures.
- **Why separate?**: Monitoring must be independent of the monitored services.

## 8. The Dashboard ("The Face")

**Role:** Local Status & Diagnostics
**Status:** Standard priority

- **Function**: User interface for checking the device status locally and exploring data.
- **Tech Stack**: Modern Web App (Python/FastAPI).
- **Modules**:
  - **BirdStats**: Statistics on detected species.
  - **BirdDiscover**: Gallery and details of detected birds.
  - **System Status**: Disk usage, uptime, service health.
