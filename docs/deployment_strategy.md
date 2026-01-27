# Silvasonic Deployment Strategy (Future Roadmap)

This document outlines the proposed architectural changes for the Silvasonic installation and deployment process. The goal is to evolve the current "Developer/Research" setup into a robust "Appliance/Fleet" model.

## 🎯 Objectives

1.  **Zero-Touch Provisioning**: Eliminate the need for SSH and manual interaction during the initial setup.
2.  **Consumer Ease-of-Use**: A "Flash & Go" experience similar to consumer electronics or simpler projects like BirdNET-Pi.
3.  **Fleet Management**: Enable centralized management of 50+ devices via Ansible and VPN from Day 1.
4.  **Robustness**: Maintain the reliability of the NVMe-only, Container-based architecture.

## 🏗️ Proposed Architecture

The core of the new strategy is the **"Silvasonic Installer Image"**.

### 1. The Installer Image (SD Card)

Instead of asking the user to manually prepare a stick with scripts, we provide a pre-built SD card image that acts as an automated technician.

- **Concept**: A minimal Raspberry Pi OS Lite image containing a `bootstrap` service.
- **Workflow**:
  1.  User flashes `silvasonic-installer.img` to an SD card.
  2.  (Optional) User edits `config.txt` inside the boot partition to set WiFi credentials and partial secrets (Fleet Key).
  3.  User inserts SD card into a Pi 5 (which has a blank NVMe SSD installed).
  4.  User powers on the Pi.

### 2. The Bootstrap Process (Automated)

Upon boot, the `bootstrap` service on the SD card executes automatically:

1.  **Hardware Check**: Verifies presence of NVMe SSD.
2.  **Flash**: `dd`'s the target OS image onto the NVMe SSD.
3.  **Inject Config**: Mounts the fresh NVMe partition and injects:
    - WiFi Credentials (from SD config).
    - Hostname (random or pre-set).
    - SSH Public Keys (embedded in Installer).
    - VPN Auth Key (Tailscale/Headscale).
4.  **Signal & Shutdown**: The Pi beeps or blinks a specific LED pattern to indicate success, then powers off.

### 3. The Target Runtime (NVMe)

When the user removes the SD card and powers on the Pi again:

1.  **Boot**: The Pi boots directly from NVMe (Gen 3 speed).
2.  **Auto-Expansion**: Filesystem expands to fill the disk.
3.  **Connectivity**: Device connects to WiFi and immediately establishes the VPN tunnel.
4.  **Provisioning Phase**:
    - **Single User Mode**: A local systemd service pulls the latest containers and starts the dashboard.
    - **Fleet Mode**: The device idles, waiting for the Fleet Controller (Ansible) to push the specific configuration for this "Node ID".

## 🛠️ Implementation Components

To achieve this, the following components need to be developed:

### A. `silvasonic-builder`

A script/pipeline to generate the `installer.img`.

- Downloads base RaspiOS.
- Installs the `bootstrap` systemd service.
- Embeds the `flash_ssd.sh` script (modified for non-interactive mode).

### B. Refactored `flash_ssd.sh`

- Add `--unattended` flag.
- Remove all interactive prompts.
- Add logic to copy `user-data` from the SD card to the NVMe target.

### C. `setup/manage.sh` (Unified CLI)

Replace `install.sh` with a tool that distinguishes between:

- `./setup/manage.sh provision-local`: Self-install (what `install.sh` does now).
- `./setup/manage.sh provision-fleet`: Wraps Ansible to target the inventory over VPN.

## ⚖️ Pros & Cons

| Metric              | Current Approach              | Proposed Strategy                              |
| :------------------ | :---------------------------- | :--------------------------------------------- |
| **User Setup Time** | 30-60 mins (Manual SSH)       | 5 mins (Flash & Boot)                          |
| **Complexity**      | High (Requires Ansible on PC) | Low (Plug & Play)                              |
| **Maintainability** | Medium (Shell scripts)        | High (Image Builder Pipeline)                  |
| **Fleet Scale**     | Linear effort (SSH into each) | Constant effort (Ansible Push)                 |
| **Security**        | Secrets on PC                 | Secrets temporarily on SD (Risk: Lost SD card) |

## 📅 Roadmap / Next Steps

1.  Prototype `flash_ssd.sh --unattended`.
2.  Create the `silvasonic-builder` script.
3.  Test the full "Flash SD -> Boot NVMe" cycle.
4.  Integrate VPN auto-enrollment.
