# Deployment Guide

This guide details how to deploy Silvasonic to a Raspberry Pi 5.

## Prerequisites

- **Hardware**: Raspberry Pi 5
- **Microphone**: Dodotronic Ultramic384 EVO (or USB microphone)
- **Storage**: NVMe SSD mounted at `/mnt/data` (Critical!)
- **OS**: Raspberry Pi OS (Bookworm)

## 1. Access Repository

> **Note**: If you ran `setup/install.sh`, the repository is already cloned at `/mnt/data/dev/silvasonic`.

```bash
cd /mnt/data/dev/silvasonic
git pull
```

## 2. Prepare Storage Directories

The services require specific directories on the NVMe drive.

```bash
# Create base service directory
sudo mkdir -p /mnt/data/dev_workspaces/silvasonic

# Create sub-directories owned by the user (or container user)
sudo mkdir -p /mnt/data/dev_workspaces/silvasonic/recorder/recordings
sudo mkdir -p /mnt/data/dev_workspaces/silvasonic/logs
sudo mkdir -p /mnt/data/dev_workspaces/silvasonic/status
sudo mkdir -p /mnt/data/dev_workspaces/silvasonic/errors
sudo mkdir -p /mnt/data/dev_workspaces/silvasonic/db/data

# Set permissions (Adjust user if needed, assumed 'pi' or current user)
sudo chown -R $USER:$USER /mnt/data/dev_workspaces/silvasonic
```

## 3. Configure Environment

Copy and edit the configuration file:

```bash
cp config.example.env .env
nano .env
```

Set your Cloud credentials (Nextcloud/Rclone) and generic settings.

## 4. Build & Run

> ⚠️ **Important**: Use `sudo` with Podman for audio device access!

```bash
# Build and start
sudo podman-compose -f podman-compose.yml up --build -d

# Check status
sudo podman ps

# View logs
sudo podman logs -f silvasonic_recorder
```

## 5. Verify Recordings

```bash
ls -la /mnt/data/dev_workspaces/silvasonic/recorder/recordings/
```

You should see WAV files (recording first) or processed artifacts.

## Configuration Options

The system uses a strict hierarchy: **Database > Environment Variables > Config Files**.

| Environment Variable | Description                   | Default |
| -------------------- | ----------------------------- | ------- |
| `MOCK_HARDWARE`      | Generate fake audio (testing) | `false` |

## Troubleshooting

### "No audio device found"

1. Check if microphone is connected: `arecord -l`
2. Ensure you're using `sudo` with Podman.

### Permission Denied

Ensure directories in `/mnt/data/dev_workspaces/silvasonic` utilize the correct SELinux labels if on Fedora/CentOS, or have correct ownership.

```bash
# Force ownership
sudo chown -R 1000:1000 /mnt/data/dev_workspaces/silvasonic
```

## Contributing Microphone Profiles

To add support for a new microphone, create a YAML file in `containers/recorder/src/microphones/`. These are mounted to `/app/mic_profiles` in the container.
