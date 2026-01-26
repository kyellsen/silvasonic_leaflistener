# 🚀 Getting Started with Silvasonic

> **Minimal SD + GitHub Clone**: The setup stick only contains bootstrap scripts. The actual repository is always cloned fresh from GitHub during installation.

This guide takes you from a brand new Raspberry Pi 5 to a fully running Silvasonic bioacoustic station.

---

## 📋 Prerequisites

To deploy Silvasonic, you need:

1.  **Hardware**:
    - **Raspberry Pi 5** (Recommended) or Pi 4.
    - **NVMe SSD + HAT**: For reliable, high-speed storage (The "Primary Drive").
    - **SD Card or USB Stick**: Only needed temporarily for the bootstrap process.
    - **Power Supply**: Reliable official power supply.

2.  **Workstation**:
    - A Linux or macOS computer.
    - `ansible` installed (`sudo apt install ansible` or `brew install ansible`).

---

## 🗺️ Installation Overview

The installation follows a "Bootstrap" pattern to ensure a clean, reproducible state.

| Phase                | Description                                             | Where                 |
| :------------------- | :------------------------------------------------------ | :-------------------- |
| **1. Prepare Stick** | Create a minimal boot stick with OS + Bootstrap Config. | Workstation           |
| **2. Flash NVMe**    | install OS and Config onto the NVMe SSD.                | Raspberry Pi          |
| **3. Provision**     | Clone repo, install packages, and start containers.     | Workstation (via SSH) |

---

## Phase 1: Create Boot Stick (Workstation)

In this phase, we prepare a temporary SD card (or USB stick) that acts as the installer.

### 1.1 Configure Credentials

On your workstation, navigate to the repo and set up your secrets.

```bash
cd dev/silvasonic
mkdir -p setup/config
cp setup/config/bootstrap.example.env setup/config/bootstrap.env
nano setup/config/bootstrap.env
```

**Required Settings:**

- `USER_PASSWORD_HASH`: Generate with `echo 'your_password' | openssl passwd -6 -stdin`
- `SSH_PUB_KEY`: Copy content from `~/.ssh/id_rsa.pub` (or similar).

### 1.2 Flash OS to SD Card

Use **Raspberry Pi Imager** to flash **Raspberry Pi OS Lite (64-bit)** to your SD card.

- _Note: No OS customization settings are needed in the Imager since we inject them next._

### 1.3 Inject Bootstrap Scripts

Run the helper script to copy the necessary files to the SD card. ensure the SD card is mounted.

```bash
# Example: Assuming SD card is mounted at /run/media/user/bootfs
# Usage: ./setup/bootstrap/prepare_stick.sh [MOUNT_POINT]
sudo ./setup/bootstrap/prepare_stick.sh
```

**What this does:**

- Copies `flash_ssd.sh` (The installer).
- Copies `bootstrap.env` (Your credentials).
- **Does NOT** copy the repository code (that comes later).

---

## Phase 2: Flash NVMe (Raspberry Pi)

Now we move to the device itself.

1.  **Insert SD Card** into the Raspberry Pi and power it on.
2.  **SSH into the Pi**:
    ```bash
    ssh pi@silvasonic.local
    # Password: As defined in your bootstrap.env (or default 'raspberry' if not set)
    ```
3.  **Run the Flasher**:
    This script will install the OS onto the NVMe drive and configure it with your users and keys.
    ```bash
    cd ~/setup_files
    sudo ./flash_ssd.sh
    ```
4.  **Power Off & Switch**:
    ```bash
    sudo poweroff
    ```
5.  **Remove the SD Card**. The Pi is now ready to boot from NVMe.

---

## Phase 3: Provisioning (Workstation)

Power on the Raspberry Pi (with only the NVMe drive). Now we use Ansible to turn it into a Silvasonic station.

> [!WARNING]
> **"Remote Host Identification Changed"**: Since you switched from SD to NVMe, the SSH fingerprint has changed.
> Run `ssh-keygen -R silvasonic.local` on your workstation to clear the old key.

### 3.1 Run Installation

From your workstation:

```bash
cd /mnt/data/dev/packages/silvasonic
./setup/install.sh
```

**What happens:**

1.  **Connects** to the Pi via SSH using the keys you configured.
2.  **Syncs** the local repository code to `/mnt/data/dev/silvasonic`.
3.  **Installs** system dependencies (podman, python, drivers).
4.  **Builds** the container images.
5.  **Starts** the `silvasonic` system service.

---

## 🏁 Verification

Your station should now be running.

**Check Logs**:

```bash
ssh admin@silvasonic.local
journalctl -fu silvasonic
```

**Access Dashboard**:
Open `http://silvasonic.local:8080` in your browser.

---

## 🔄 Updates & Deployment

To deploy code changes from your local machine to the Pi, simply run the installer again. It is designed to be idempotent (only changes what is necessary).

```bash
# From your workstation
./setup/install.sh
```
