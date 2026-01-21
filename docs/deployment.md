# Deployment Guide

This guide details how to deploy Silvasonic to a Raspberry Pi 5.

## Prerequisites

- **Hardware**: Raspberry Pi 5.
- **Microphone**: Dodotronic Ultramic384 EVO (or USB equivalent).
- **Storage**: NVMe SSD mounted at `/mnt/data` (Critical!).
- **OS**: Raspberry Pi OS (Bookworm) or Fedora IoT.

## 1. Setup Repository

On the Raspberry Pi:

```bash
# Navigate to data partition
cd /mnt/data/dev

# Clone repository
git clone https://github.com/kyellsen/silvasonic_leaflistener.git
cd silvasonic_leaflistener
```

## 2. Configuration

Create your environment file:

```bash
# Copy example env
cp .env.example .env

# Edit settings (Optional)
# AUDIO_DEVICE_NAME="Ultramic"
```

## 3. Build & Run

We use **Podman** and **Podman Compose** (via `podman-compose`).

```bash
# Build and Start in detached mode
podman-compose -f podman-compose.yml up --build -d
```

### Note on Docker

If using legacy Docker:

```bash
docker compose up --build -d
```

## 4. Verification

1. **Check Containers**:

   ```bash
   podman ps
   ```

   You should see `silvasonic_ear`.

2. **Check Logs**:

   ```bash
   podman logs silvasonic_ear
   ```

   Look for: `[INFO] Recording started.`

3. **Verify Audio**:
   Check if files are being created:
   ```bash
   ls -la /mnt/data/storage/leaflistener/raw/
   ```

## Troubleshooting

### "Device not found"

- Run `lsusb` to check if microphone is detected.
- Check logs: `podman logs silvasonic_ear`. It will list available devices if target is missing.
- Ensure the container has permissions (running as privileged or with `--device /dev/snd`).

### "Permission Denied" (Storage)

- Ensure `/mnt/data` is writable by the container user.
- If using SELinux (Fedora), ensure volumes are mounted with `:z`.
