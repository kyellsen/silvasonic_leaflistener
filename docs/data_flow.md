# Data Flow & Storage Strategy

## Storage Hierarchy

1.  **RAM Buffer**: Audio is captured into a ring buffer in memory to smooth out IO latency.
2.  **NVMe SSD (`/mnt/data/services/silvasonic`)**:
    - Primary persistent storage for recordings and application state.
    - **Raw Recordings**: `/mnt/data/services/silvasonic/recorder/recordings`
    - **Database**: `/mnt/data/services/silvasonic/db/data` (PostgreSQL)
    - **Logs**: `/mnt/data/services/silvasonic/logs`
    - **Recycle Policy**: Oldest recordings are deleted when disk usage triggers limits.

## Compression

- **Format**: FLAC (Free Lossless Audio Codec).
- **Benefit**: Reduces file size by ~40-50% compared to raw WAV.
- **Cpu Usage**: Encoding is done on "The Ear" container.

## Synchronization (The Mirror)

The system uses a "Store & Forward" approach managed by the **Uploader** container.

### Transport

- **Tools**: Rclone (primary) or Syncthing.
- **Method**: Files are synced to a central server/cloud (Nextcloud, S3, SFTP).
- **Safety**: The Uploader mounts recordings as Read-Only (or managed) to prevent accidental deletions on the source.

## File System Layout

The system uses a strict directory structure on the NVMe drive (`/mnt/data`).

- **Infrastructure**: `/mnt/data/containers` (Volumes, Stacks, Storage)
- **Dev Workspace**: `/mnt/data/dev` (Repo checkouts)
- **Service Data**: `/mnt/data/services/silvasonic`
  - `recorder/recordings`: FLAC files.
  - `uploader/config`: Rclone/Sync config.
  - `birdnet/results`: Analysis results (if file-based).
  - `sound_analyser/artifacts`: Spectrograms/Plots.
  - `db/data`: Postgres data.

### Transient Scripts

Any temporary, investigative, or verification scripts (e.g. `verify_audio.py`) must be placed in `scripts/temp/`. They must **never** be placed in the project root.
