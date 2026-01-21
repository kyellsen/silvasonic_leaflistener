# Deployment Guide

This guide details how to deploy Silvasonic to a Raspberry Pi 5.

## Prerequisites

- **Hardware**: Raspberry Pi 5
- **Microphone**: Dodotronic Ultramic384 EVO (or USB microphone)
- **Storage**: NVMe SSD mounted at `/mnt/data` (Critical!)
- **OS**: Raspberry Pi OS (Bookworm) or Fedora IoT

## Supported Microphones

The recorder auto-detects microphones via profiles. Currently supported:

| Microphone                   | Sample Rate | Use Case         |
| ---------------------------- | ----------- | ---------------- |
| Dodotronic Ultramic 384K EVO | 384 kHz     | Bats, Ultrasound |
| Generic USB Microphone       | 48 kHz      | Birds, General   |

To add support for new microphones, see [Contributing Microphone Profiles](#contributing-microphone-profiles).

## 1. Access Repository

> **Note**: If you ran `setup/install.sh`, the repository is already cloned at `/mnt/data/dev/silvasonic_leaflistener`.

```bash
cd /mnt/data/dev/silvasonic_leaflistener
git pull
```

**Manual Clone (if needed):**

```bash
cd /mnt/data/dev
git clone https://github.com/kyellsen/silvasonic_leaflistener.git
cd silvasonic_leaflistener
```

## 2. Create Storage Directory

```bash
sudo mkdir -p /mnt/data/storage/leaflistener/raw
sudo chown $USER:$USER /mnt/data/storage/leaflistener/raw
```

## 3. Build & Run

> ⚠️ **Important**: Use `sudo` with Podman for audio device access!

```bash
# Build and start
sudo podman-compose -f podman-compose.yml up --build -d

# Check status
sudo podman ps

# View logs
sudo podman logs -f silvasonic_ear
```

### Expected Log Output

```
🎤 THE EAR - Silvasonic Audio Recorder
==============================================================
Profile: Dodotronic Ultramic 384K EVO
  Manufacturer: Dodotronic
  Sample Rate: 384000 Hz
  Channels: 1
  Bit Depth: 16
  Chunk Duration: 60s
  Device: hw:0,0
🎙️ Recording started. Press Ctrl+C to stop.
Recording 60s -> 2026-01-21_16-09-11.flac
Saved: 2026-01-21_16-09-11.flac (14.02 MB)
```

## 4. Verify Recordings

```bash
ls -la /mnt/data/storage/leaflistener/raw/
```

You should see FLAC files with timestamps.

## Configuration Options

The recorder auto-detects configuration from microphone profiles. For advanced use:

| Environment Variable | Description                   | Default           |
| -------------------- | ----------------------------- | ----------------- |
| `MOCK_HARDWARE`      | Generate fake audio (testing) | `false`           |
| `AUDIO_PROFILE`      | Force specific profile name   | Auto-detect       |
| `AUDIO_OUTPUT_DIR`   | Recording output directory    | `/data/recording` |

Example with mock mode:

```bash
sudo podman-compose -f podman-compose.yml down
sudo MOCK_HARDWARE=true podman-compose -f podman-compose.yml up -d
```

## Troubleshooting

### "No audio device found"

1. Check if microphone is connected:

   ```bash
   arecord -l
   ```

2. Ensure you're using `sudo` with Podman:

   ```bash
   sudo podman logs silvasonic_ear
   ```

3. Verify device permissions:
   ```bash
   ls -la /dev/snd/
   ```

### Container restarts repeatedly

Check logs for errors:

```bash
sudo podman logs silvasonic_ear --tail 50
```

Common causes:

- Missing microphone
- Permission issues
- Incorrect sample rate for device

### Permission Denied (Storage)

```bash
sudo chown -R $USER:$USER /mnt/data/storage/leaflistener/
```

If using SELinux (Fedora):

```bash
sudo chcon -Rt container_file_t /mnt/data/storage/leaflistener/
```

## Contributing Microphone Profiles

To add support for a new microphone:

1. Create a YAML file in `containers/sensor/recorder/microphones/`
2. Follow the template in `dodotronic_ultramic384k.yml`
3. Test with your hardware
4. Submit a Pull Request

### Profile Template

```yaml
name: "Your Microphone Name"
manufacturer: "Manufacturer"
device_patterns:
  - "Pattern in arecord -l output"
audio:
  sample_rate: 48000
  channels: 1
  bit_depth: 16
recording:
  chunk_duration_seconds: 60
```

See `containers/sensor/recorder/microphones/` for examples.
