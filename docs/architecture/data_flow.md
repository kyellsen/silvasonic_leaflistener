# Data Flow & Storage Strategy

## Storage Hierarchy

1.  **RAM Buffer**: Audio is captured into a ring buffer in memory to smooth out IO latency.
2.  **NVMe SSD (`/mnt/data/services/silvasonic`)**:
    - Primary persistent storage for recordings and application state.
    - **Raw Recordings**: `/mnt/data/services/silvasonic/data/recordings` (WAV First)
    - **Database**: `/mnt/data/services/silvasonic/db/data` (PostgreSQL)
    - **Logs**: `/mnt/data/services/silvasonic/logs`
    - **Recycle Policy**: Oldest recordings are deleted by the **Janitor** (Processor) when disk usage triggers limits.

## Compression

- **Format**: FLAC (Free Lossless Audio Codec).
- **Strategy**: **"Record First"**. The Recorder writes raw `.wav` to disk (low CPU). The **Uploader** then converts to `.flac` *before* uploading to the cloud to save bandwidth.
- **Benefit**: Stability (no encoding overlap during recording) + Bandwidth savings.

## Synchronization (The Mirror)

The system uses a "Store & Forward" approach managed by the **Uploader** container.

### Transport

- **Tools**: Rclone (primary) or Syncthing.
- **Method**: Files are synced to a central server/cloud (Nextcloud, S3, SFTP).
- **Process**: WAV -> FLAC (Temp) -> Upload -> Delete Temp.

## File System Layout

The system uses a strict directory structure on the NVMe drive (`/mnt/data`).

- **Infrastructure**: `/mnt/data/containers` (Volumes, Stacks, Storage)
- **Dev Workspace**: `/mnt/data/dev` (Repo checkouts)
- **Service Data**: `/mnt/data/services/silvasonic`
  - `data/recordings`: WAV files (High-Res and Low-Res).
  - `config`: Configuration files.
  - `db/data`: Postgres data.

### Transient Scripts

Any temporary, investigative, or verification scripts (e.g. `verify_audio.py`) must be placed in `.agent_tmp/`. They must **never** be placed in the project root or `scripts/temp/`.
