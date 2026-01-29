# Microphone Profiles

This directory contains YAML configuration files for supported microphones.

## How It Works

When the recorder starts, it:

1. Scans for connected USB audio devices using `arecord -l`
2. Matches device names against patterns in each profile
3. Applies the matched profile's audio settings automatically

## Available Profiles

| File                          | Microphone                    | Sample Rate |
| ----------------------------- | ----------------------------- | ----------- |
| `dodotronic_ultramic384k.yml` | Dodotronic Ultramic 384K EVO  | 384 kHz     |
| `generic_usb.yml`             | Any USB Microphone (fallback) | 48 kHz      |
| `mock.yml`                    | Virtual Device (testing)      | 48 kHz      |

## Contributing a New Profile

1. Connect your microphone and run:

   ```bash
   arecord -l
   ```

   Note the device name shown (e.g., "Rode NT-USB Mini")

2. Create a new YAML file in this directory:

   ```bash
   cp generic_usb.yml my_microphone.yml
   ```

3. Edit the profile:

   ```yaml
   name: "Your Microphone Name"
   manufacturer: "Brand"

   device_patterns:
     - "Part of the name from arecord -l"

   audio:
     sample_rate: 48000 # Check your mic's specs
     channels: 1
     bit_depth: 16

   recording:
     chunk_duration_seconds: 60
   ```

4. Test locally:

   ```bash
   podman-compose -f podman-compose.yml up --build -d
   podman logs silvasonic_recorder
   ```

5. Submit a Pull Request!

## Profile Priority

Profiles are matched in order of:

1. Specificity (more specific patterns match first)
2. Priority field (lower number = higher priority)
3. File load order

The `generic_usb.yml` has `priority: 100` to ensure it's only used as a fallback.
