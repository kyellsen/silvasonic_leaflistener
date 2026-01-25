# Container Architecture

The Silvasonic architecture is designed around resiliency. The system is split into logical blocks, each isolated in its own container to ensure that critical functions (recording) are not affected by secondary tasks (UI, Uploads).

## 1. The Recorder ("The Ear")

**Role:** Critical Audio Capture
**Status:** Privileged / Real-time priority

- **Function**: Captures audio directly from the Dodotronic Ultramic384 EVO via ALSA/SoundDevice.
- **Operation**:
  - Buffers audio in RAM to avoid dropped samples.
  - Writes compressed **.flac** files to the NVMe SSD (`/mnt/data/services/silvasonic/recorder/recordings`).
- **Why separate?**: This container is "sacred". It must never crash or be stopped, even if the dashboard fails or the network hangs.

## 2. The Uploader ("The Carrier")

**Role:** Data Sync & Transport
**Status:** Low priority background process

- **Function**: Synchronizes recorded files to the central server (Nextcloud/WebDAV or Rsync).
- **Technology**: Custom Python wrapper (`uploader` container) handling sync logic.
- **Mounts**: Mounts the storage directory with managed access to prevent accidental deletion or corruption by the sync process.
- **Why separate?**: Network operations can be resource-intensive or hang. Isolating this ensures that a stuck upload doesn't block the recording loop.

## 3. BirdNET ("The Brain")

**Role:** Species Classification
**Status:** Standard priority

- **Function**: Analyzes audio files to detect and classify bird species using the BirdNET model.
- **Operation**:
  - Watches for new recordings.
  - Processes audio segments to generate detection entries.
  - Stores results in a local database for the Dashboard.
- **Why separate?**: Inference is CPU/RAM heavy. It must run decoupled from the recording loop.

## 4. The Dashboard ("The Face")

**Role:** Local Status & Diagnostics
**Status:** Standard priority

- **Function**: User interface for checking the device status locally and exploring data.
- **Tech Stack**: Modern Web App (Python/FastAPI).
- **Modules**:
  - **BirdStats**: Statistics on detected species.
  - **BirdDiscover**: Gallery and details of detected birds.
  - **System Status**: Disk usage, uptime, service health.

## 5. The HealthChecker ("The Watchdog")

**Role:** Monitoring & Alerts
**Status:** High Availability / Watchdog

- **Function**: Monitors the health of other containers and system resources.
- **Features**:
  - **Service Checks**: Verifies that Recorder, Uploader, etc., are running and responsive.
  - **Log Rotation**: Manages log sizes to prevent disk overflow.
  - **Alerting**: Sends notifications (e.g., email) on critical failures or if the "Dead Man's Switch" is triggered.
- **Why separate?**: Monitoring must be independent of the monitored services. If other containers freeze, the HealthChecker remains alive to attempt recovery or alert the admin.

## 6. SoundAnalyser (Custom/Experimental)

**Role:** Specialized Analysis
**Status:** Standard priority

- **Function**: Framework for running additional or custom acoustic analysis beyond BirdNET.
- **Use Case**: Bat detection, specific insect frequencies, or experimental models.
