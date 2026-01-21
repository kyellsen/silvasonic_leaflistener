# Silvasonic Setup Guide

> [!IMPORTANT]
> **Context**: All commands in this guide assume you are running them from the **root directory** of this repository (e.g., `~/silvasonic_leaflistener/`).

This repository contains scripts and Ansible playbooks to fully automate the setup of a Raspberry Pi 5 (Silvasonic).

## Prerequisites

- Raspberry Pi 5 (or 4, though NVMe optimizations are for 5)
- NVMe SSD installed
- Micro-SD Card (as temporary boot medium for flashing the SSD)
- PC/Mac for preparing the SD card
- OS Image: Download the desired image (e.g., Raspberry Pi OS Lite 64-bit) and ideally place it in the root directory of this repo or into `setup/bootstrap/`.

## Structure

- `setup/config.example.env`: Template for all settings (User, WiFi, passwords).
- `setup/bootstrap/`: Scripts for the initial boot stick and SSD flashing.
- `setup/provision/`: Ansible Playbooks for the final setup.
- `scripts/`: Useful scripts for ongoing operation (`check.sh`, `sound_check.sh`).

---

## A) Create Bootstick (First Boot)

Goal: Create a bootable USB stick/SD card containing the installation script and the target image.

### 1. Prepare Configuration

1.  Copy `setup/config.example.env` to `setup/config/config.env`.
    ```bash
    cp setup/config.example.env setup/config/config.env
    ```
2.  **EDIT** `setup/config/config.env` and set your passwords, SSH keys, and WiFi details.

### 2. Flash SD Card

1.  Use **Raspberry Pi Imager**.
2.  Select OS: `Raspberry Pi OS Lite (64-bit)`.
3.  Select SD Card.
4.  **IMPORTANT**: You can skip "OS Customisation" in the Imager, as our script automatically creates `userconf.txt` and `ssh`.
5.  Click "WRITE".

### 3. Copy Setup Files to Stick

After flashing, briefly remove and re-insert the SD card so that the partitions (`bootfs` and `rootfs`) are recognized/mounted by your PC.

Use the helper script `prepare_stick.sh`. It is interactive and automatically detects your stick (and adjusts the size).

```bash
# Interactive Mode (Recommended):
sudo ./setup/bootstrap/prepare_stick.sh
```

**What this script does:**

1.  Lists **only** removable media (USB/SD) (Security filter).
2.  You select your stick.
3.  Automatically expands the partition (to make room for the image).
4.  Creates `ssh` and `userconf.txt` (Login on the stick: User **`pi`**, Password = your Admin Password from the config).
5.  Enables PCIe Gen 3.
6.  Copies the repo (`setup/`, `scripts/`), the config, and the OS image into the home directory on the stick (`/home/pi/setup_files/`).

---

## B) Installation on NVMe SSD

### 1. Boot from Stick

1.  Insert SD card into the Raspberry Pi.
2.  Power on the Pi.
3.  Connect via SSH (or local keyboard/screen).
    ```bash
    ssh pi@silvasonic.local
    # Password is the one you generated the hash for in the config (Default: admin)
    ```

### 2. Flash SSD

Run the flash script on the Pi (located in the home directory, thanks to step A):

```bash
cd ~/setup_files
sudo ./flash_ssd.sh
```

- The script writes the image to the NVMe.
- Creates partitions.
- Pre-configures User, SSH, and Hostname on the SSD.

After completion:

```bash
sudo poweroff
```

Remove the SD Card!

---

## C) Final Provisioning (Ansible)

Restart the Pi (**without SD card**; it will now boot from the NVMe).

### 1. Connect

```bash
ssh admin@silvasonic.local
```

### 2. Start Setup

Since `flash_ssd.sh` (from Step B) has already copied all setup files to the SSD, you can start immediately:

```bash
cd ~/silvasonic_leaflistener

# Run the install script
sudo ./setup/install.sh
```

_(If you skipped Step B, you must clone the repo first: `git clone ...`)_

The `install.sh` script:

1.  Reads your `setup/config/config.env`.
2.  Installs Ansible.
3.  Configures WiFi, Packages, Podman, Audio, and Storage structure via Ansible.

### 3. Checks

Run the health check:

```bash
~/check.sh
~/sound_check.sh
```

Done!
