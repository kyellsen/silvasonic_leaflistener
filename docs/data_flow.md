# Data Flow & Storage Strategy

## Storage Hierarchy

1.  **RAM Buffer**: Audio is captured into a ring buffer in memory to smooth out IO latency.
2.  **NVMe SSD (`/mnt/data/storage`)**:
    - Primary persistent storage.
    - Files are written immediately as **.flac** to save space and write bandwidth.
    - Retention: Capable of holding several days/weeks of raw audio (512GB capacity).
    - **Cache Policy**: Oldest files are deleted only when disk usage exceeds a high watermark (e.g., 90%).

## Compression

- **Format**: FLAC (Free Lossless Audio Codec).
- **Benefit**: Reduces file size by ~40-50% compared to raw WAV without losing any bioacoustic data.
- **Cpu Usage**: Encoding is done on "The Ear" container.

## Synchronization (The Mirror)

The system uses a "Store & Forward" approach.

### Transport

- **Tools**: Syncthing (preferred for continuous sync) or Rsync (for scheduled batches).
- **VPN**: If the device is outside the local network, traffic is routed through **Tailscale** or **Wireguard** to the central server.

### Destination (Server/NAS)

- The central server acts as a mirror.
- It runs a companion Syncthing instance.
- **Fleet Monitoring**: A `fleet_monitor` service on the server tracks the "Last Seen" timestamp of files from each device to alert if a station goes silent.

## File System Layout

The system uses a strict directory structure on the NVMe drive (`/mnt/data`). All agents and services must adhere to these canonical paths:

- **Infrastructure**: `/mnt/data/containers` (Volumes, Stacks, Storage)
- **Development**: `/mnt/data/dev` (Repo checkouts)
- **Raw Recordings**: `/mnt/data/services/silvasonic/recordings` (Recorders write here)
- **Processed Data**: `/mnt/data/storage/silvasonic/processed`
- **Export/Results**: `/mnt/data/storage/silvasonic/results`

### Transient Scripts

Any temporary, investigative, or verification scripts (e.g. `verify_audio.py`) must be placed in `scripts/temp/`. They must **never** be placed in the project root.
