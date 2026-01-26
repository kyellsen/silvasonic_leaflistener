#!/usr/bin/env bash
set -euo pipefail

# ===================== CONFIG =====================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/../config/bootstrap.env"
STICK_USER="pi"

# Load Config
if [[ ! -f "$CONFIG_FILE" ]]; then
    if [[ -f "$SCRIPT_DIR/config.env" ]]; then
         CONFIG_FILE="$SCRIPT_DIR/config.env"
    else
         echo "ERROR: Config file not found. setup/config.example.env -> setup/config/bootstrap.env"
         exit 1
    fi
fi
source "$CONFIG_FILE"

STICK_PASSWORD_HASH="$USER_PASSWORD_HASH"

# Dependencies
for cmd in parted resize2fs lsblk; do
    if ! command -v $cmd &> /dev/null; then
        echo "ERROR: Missing command '$cmd'. Please install (e.g. sudo apt install parted)."
        exit 1
    fi
done

# ===================== HELPER =====================
log() { echo -e "\033[0;34m[PREPARE]\033[0m $*"; }
error() { echo -e "\033[0;31m[ERROR]\033[0m $*" >&2; exit 1; }

# ===================== PARSE ARGS & SELECT DEVICE =====================
DEVICE=""
BOOT_MNT=""
ROOT_MNT=""
AUTO_MOUNTED=false

usage() {
    echo "Usage: sudo $0 [device] (e.g. /dev/mmcblk0)"
    echo "       If no device is provided, an interactive menu will appear."
    exit 1
}

# Check if first arg is a device or flag
if [[ "$#" -gt 0 ]] && [[ "$1" == /dev/* ]]; then
    DEVICE="$1"
    shift
elif [[ "$#" -gt 0 ]] && [[ "$1" == -* ]]; then
    # Flags mode (legacy manual mounts)
    while [[ $# -gt 0 ]]; do
      case $1 in
        --boot) BOOT_MNT="$2"; shift 2 ;;
        --root) ROOT_MNT="$2"; shift 2 ;;
        *) usage ;;
      esac
    done
fi

# INTERACTIVE MODE if no device and no manual mounts
if [[ -z "$DEVICE" ]] && [[ -z "$BOOT_MNT" ]]; then
    echo "--- Interactive Device Selection ---"
    
    # 1. Identify Root Device (to hide/protect it) (Robust method)
    ROOT_MOUNT_SOURCE=$(findmnt / -o SOURCE -n)
    # Remove potential [subvol] suffix (e.g. /dev/mapper/xxx[/@])
    ROOT_MOUNT_SOURCE="${ROOT_MOUNT_SOURCE%%\[*}"
    
    ROOT_DISK="unknown"
    if [[ -b "$ROOT_MOUNT_SOURCE" ]]; then
         # Get the physical disk at the end of the chain
         # lsblk -s lists dependencies in reverse order (leaf to root). The last line is the disk.
         ROOT_DISK=$(lsblk -no NAME -s "$ROOT_MOUNT_SOURCE" | tail -n1)
    fi
    
    # 2. List Candidates
    # Filter: PROT=USB or NAME=mmcblk*
    
    echo "Scanning for removable media (USB / SD)..."
    # Get list of disks: NAME, SIZE, TRAN, MODEL
    # We use -d to only show disks, not partitions
    
    CANDIDATES=()
    i=1
    
    # Read lsblk output line by line. 
    # Output format: NAME SIZE TRAN MODEL (TRAN might be empty)
    while read -r name size tran model; do
        # construct full path
        devpath="/dev/$name"
        
        # Skip if it is the root disk
        if [[ "$name" == "$ROOT_DISK" ]]; then
             continue
        fi

        # SECURITY FILTER:
        # Only allow if TRAN is 'usb' OR name starts with 'mmcblk'
        is_usb=0
        [[ "$tran" == "usb" ]] && is_usb=1
        [[ "$name" == mmcblk* ]] && is_usb=1
        
        if [[ $is_usb -eq 0 ]]; then
            # Skip internal drives (nvme, sata, etc)
            continue
        fi
        
        # Display
        echo "$i) $devpath ($size) [$tran] $model"
        CANDIDATES+=("$devpath")
        ((i++))
    done < <(lsblk -d -n -o NAME,SIZE,TRAN,MODEL | grep -v "loop" | grep -v "ram")
    
    if [[ ${#CANDIDATES[@]} -eq 0 ]]; then
        echo "No suitable removable drives (USB/SD) found."
        echo "  (Internal drives are hidden for safety)"
        exit 1
    fi
    
    echo
    read -p "Select drive number [1-$((i-1))]: " selection
    
    # Validate
    idx=$((selection-1))
    if [[ -z "${CANDIDATES[$idx]}" ]]; then
        echo "Invalid selection."
        exit 1
    fi
    
    DEVICE="${CANDIDATES[$idx]}"
    echo "Selected: $DEVICE"
    echo
fi

# ===================== DEVICE LOGIC (RESIZE & MOUNT) =====================
if [[ -n "$DEVICE" ]]; then
    if [[ ! -b "$DEVICE" ]]; then
        error "Device $DEVICE not found or not a block device."
    fi

    # Confirm
    echo -e "\033[0;33m"
    lsblk "$DEVICE"
    echo -e "\033[0m"
    read -p "WARNING: Stick preparation on $DEVICE. Partition 2 will be resized and mounted. Continue? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error "Aborted by user."
    fi

    log "Checking mounted partitions on $DEVICE..."
    # Unmount everything on device to be safe for resize
    for mount in $(lsblk -n -o MOUNTPOINT "$DEVICE" | grep -v "^$"); do
        log "Unmounting $mount..."
        sudo umount "$mount"
    done

    # RESIZE PARTITION 2 (ROOTFS)
    # Usually Imager leaves creation minimal. We assume P1=Boot, P2=Root
    log "Resizing Partition 2 (Rootfs) to fill disk..."
    
    # Check if P2 exists
    if ! lsblk "${DEVICE}2" &>/dev/null && ! lsblk "${DEVICE}p2" &>/dev/null; then
         error "Partition 2 not found on $DEVICE. Is this a valid Raspi image?"
    fi
    
    # Handle nvme/mmc naming vs sda naming
    P2_DEV="${DEVICE}2"
    if [[ "$DEVICE" == *"nvme"* ]] || [[ "$DEVICE" == *"mmcblk"* ]]; then
        P2_DEV="${DEVICE}p2"
    fi
    P1_DEV="${P2_DEV%2}1"
    [[ "$DEVICE" == *"nvme"* ]] || [[ "$DEVICE" == *"mmcblk"* ]] && P1_DEV="${DEVICE}p1"

    # Parted resize (100% of stick)
    sudo parted -s "$DEVICE" resizepart 2 100%
    
    # FS resize
    log "Resizing ext4 filesystem on $P2_DEV..."
    sudo e2fsck -fy "$P2_DEV" || true
    sudo resize2fs "$P2_DEV"

    # MOUNT
    MNT_BASE="/tmp/silvasonic_setup_$(date +%s)"
    BOOT_MNT="$MNT_BASE/boot"
    ROOT_MNT="$MNT_BASE/root"
    mkdir -p "$BOOT_MNT" "$ROOT_MNT"
    
    log "Mounting $P1_DEV -> $BOOT_MNT"
    sudo mount "$P1_DEV" "$BOOT_MNT"
    log "Mounting $P2_DEV -> $ROOT_MNT"
    sudo mount "$P2_DEV" "$ROOT_MNT"
    
    AUTO_MOUNTED=true
fi

# ===================== VALIDATE MOUNTS =====================
if [[ -z "$BOOT_MNT" ]] || [[ -z "$ROOT_MNT" ]]; then
    # Try default fallback (/run/media/$USER/...) if no device given
    DEFAULT_BOOT="/run/media/${USER}/bootfs"
    DEFAULT_ROOT="/run/media/${USER}/rootfs"
    if [[ -d "$DEFAULT_BOOT" ]] && [[ -d "$DEFAULT_ROOT" ]] && [[ -z "$DEVICE" ]]; then
        BOOT_MNT="$DEFAULT_BOOT"
        ROOT_MNT="$DEFAULT_ROOT"
        log "Using default mounts: $BOOT_MNT, $ROOT_MNT"
    else
        error "No mounts specified and no device provided. Usage: sudo $0 /dev/sdX"
    fi
fi

if [[ ! -d "$BOOT_MNT" ]] || [[ ! -d "$ROOT_MNT" ]]; then
    error "Mount points invalid: $BOOT_MNT / $ROOT_MNT"
fi

# ===================== PROVISIONING (MINIMAL) =====================
TARGET_USER_HOME="$ROOT_MNT/home/$STICK_USER"

# 1. SSH & Userconf
log "Creating ssh marker..."
sudo touch "$BOOT_MNT/ssh"

log "Creating userconf.txt for '$STICK_USER'..."
echo "${STICK_USER}:${STICK_PASSWORD_HASH}" | sudo tee "$BOOT_MNT/userconf.txt" >/dev/null

# 2. Config.txt adjustments (PCIe)
if ! grep -q "dtparam=pciex1_gen=3" "$BOOT_MNT/config.txt"; then
    log "Enabling PCIe Gen 3 in config.txt..."
    echo "dtparam=pciex1_gen=3" | sudo tee -a "$BOOT_MNT/config.txt" >/dev/null
fi

# 3. Create setup_files directory with ONLY essential files
if [[ ! -d "$TARGET_USER_HOME" ]]; then
    log "Creating home dir $TARGET_USER_HOME..."
    sudo mkdir -p "$TARGET_USER_HOME"
    sudo chown 1000:1000 "$TARGET_USER_HOME"
fi

TARGET_SETUP="$TARGET_USER_HOME/setup_files"
sudo mkdir -p "$TARGET_SETUP"

# Copy ONLY flash_ssd.sh
log "Copying flash_ssd.sh..."
sudo cp "$SCRIPT_DIR/flash_ssd.sh" "$TARGET_SETUP/"
sudo chmod +x "$TARGET_SETUP/flash_ssd.sh"

# Copy bootstrap config (flattened)
log "Copying bootstrap.env..."
sudo cp "$CONFIG_FILE" "$TARGET_SETUP/bootstrap.env"

# Copy Runtime Template
RUNTIME_TEMPLATE="$SCRIPT_DIR/../../config.example.env"
if [[ -f "$RUNTIME_TEMPLATE" ]]; then
    log "Copying runtime config.example.env..."
    sudo cp "$RUNTIME_TEMPLATE" "$TARGET_SETUP/config.example.env"
fi

# Copy Image File (With space check)
if [[ -f "$IMAGE_FILE" ]]; then
    IMAGE_SIZE=$(du -k "$IMAGE_FILE" | cut -f1)
    FREE_SPACE=$(df -k --output=avail "$TARGET_USER_HOME" | tail -n1)
    NEEDED=$((IMAGE_SIZE + 10240)) # 10MB buffer

    if [[ $FREE_SPACE -lt $NEEDED ]]; then
       error "Not enough space ($((FREE_SPACE/1024))MB < $((NEEDED/1024))MB). Resize failed or stick too small."
    fi

    log "Copying Image File: $IMAGE_FILE ..."
    sudo cp "$IMAGE_FILE" "$TARGET_SETUP/"
else
    # Check relative to bootstrap dir
    REL_IMG="$SCRIPT_DIR/$IMAGE_FILE"
    if [[ -f "$REL_IMG" ]]; then
         log "Copying Image File (from bootstrap dir)..."
         sudo cp "$REL_IMG" "$TARGET_SETUP/"
    else
         log "WARNING: Image file not found. Boot stick will miss the image!"
    fi
fi

# Permissions
sudo chown -R 1000:1000 "$TARGET_USER_HOME/setup_files"

# ===================== SUMMARY =====================
log ""
log "=============================================="
log "Boot stick prepared successfully!"
log "=============================================="
log ""
log "Contents of $TARGET_SETUP:"
ls -la "$TARGET_SETUP" 2>/dev/null || sudo ls -la "$TARGET_SETUP"
log ""
log "This stick contains ONLY:"
log "  • flash_ssd.sh  (NVMe installer)"
log "  • bootstrap.env (credentials + settings)"
log "  • OS image      (to flash onto NVMe)"
log ""
log "The Silvasonic repo will be cloned from GitHub"
log "by Ansible (install.sh) after NVMe boot."
log "=============================================="

# ===================== CLEANUP =====================
if [[ "$AUTO_MOUNTED" == "true" ]]; then
    log "Unmounting... Please wait!"
    sudo umount "$BOOT_MNT"
    sudo umount "$ROOT_MNT"
    rmdir "$BOOT_MNT" "$ROOT_MNT" "$MNT_BASE"
    log "Success! You can remove $DEVICE now."
else
    log "Success! (Manual mounts kept active)"
fi
