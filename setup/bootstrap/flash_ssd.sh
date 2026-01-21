#!/usr/bin/env bash
set -euo pipefail

# ===================== LOCATE CONFIG =====================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_PREFIX="[FLASH]"
log() { echo "${LOG_PREFIX} $*"; }

# 1. Try standard repo location (setup/config/config.env relative to setup/bootstrap/flash_ssd.sh)
CONFIG_FILE="$SCRIPT_DIR/../config/config.env"

if [[ ! -f "$CONFIG_FILE" ]]; then
    # 2. Try location on stick (setup/config/config.env relative to ~/setup_files/flash_ssd.sh)
    # On stick, we have setup_files/setup/config...
    if [[ -f "$SCRIPT_DIR/setup/config/config.env" ]]; then
        CONFIG_FILE="$SCRIPT_DIR/setup/config/config.env"
    else
        log "ERROR: Config file not found."
        log "Checked: $SCRIPT_DIR/../config/config.env"
        log "Checked: $SCRIPT_DIR/setup/config/config.env"
        exit 1
    fi
fi

source "$CONFIG_FILE"

MNT_BOOT="/mnt/nvme_boot"
MNT_ROOT="/mnt/nvme_root"

# ===================== VALIDATE CONFIG =====================
: "${IMAGE_FILE:?Missing IMAGE_FILE in config}"
: "${TARGET_DISK:?Missing TARGET_DISK in config}"
: "${HOSTNAME:?Missing HOSTNAME in config}"
: "${USER_NAME:?Missing USER_NAME in config}"
: "${USER_PASSWORD_HASH:?Missing USER_PASSWORD_HASH in config}"
: "${SSH_PUB_KEY:?Missing SSH_PUB_KEY in config}"

# Handle relative image path
if [[ ! -f "$IMAGE_FILE" ]]; then
    # Try relative to script
    if [[ -f "$SCRIPT_DIR/$IMAGE_FILE" ]]; then
        IMAGE_FILE="$SCRIPT_DIR/$IMAGE_FILE"
    else
         echo "ERROR: Image file not found: $IMAGE_FILE" >&2
         exit 1
    fi
fi

cleanup() {
  mountpoint -q "$MNT_BOOT" && sudo umount "$MNT_BOOT"
  mountpoint -q "$MNT_ROOT" && sudo umount "$MNT_ROOT"
}
trap cleanup EXIT

# ===================== START ======================
log "Flashing NVMe for host '${HOSTNAME}'"
log "TARGET DISK: ${TARGET_DISK}"
log "IMAGE: ${IMAGE_FILE}"

# --- Flash image ---
log "Writing image to NVMe (this will DESTROY all data on ${TARGET_DISK})"
xz -d -c "$IMAGE_FILE" | sudo dd of="$TARGET_DISK" bs=4M status=progress conv=fsync
sudo partprobe "$TARGET_DISK"
sleep 5 # Give kernel time to update partition table

# --- Mount partitions ---
log "Mounting partitions"
sudo mkdir -p "$MNT_BOOT" "$MNT_ROOT"
# Ensure partitions exist before mounting
if [[ ! -e "${TARGET_DISK}p1" ]] || [[ ! -e "${TARGET_DISK}p2" ]]; then
    log "Error: Partitions not found. Flashing might have failed."
    exit 1
fi
sudo mount "${TARGET_DISK}p1" "$MNT_BOOT"
sudo mount "${TARGET_DISK}p2" "$MNT_ROOT"

# --- User + SSH (boot mechanism) ---
log "Provisioning user '${USER_NAME}' and enabling SSH"
echo "${USER_NAME}:${USER_PASSWORD_HASH}" | sudo tee "$MNT_BOOT/userconf.txt" >/dev/null
sudo touch "$MNT_BOOT/ssh"

# --- PCIe Gen 3 Enforce ---
# Für maximale NVMe Performance ab dem ersten Boot
if ! grep -q "dtparam=pciex1_gen=3" "$MNT_BOOT/config.txt"; then
    log "Enabling PCIe Gen 3 in config.txt"
    echo "dtparam=pciex1_gen=3" | sudo tee -a "$MNT_BOOT/config.txt"
fi

# --- Hostname ---
log "Setting hostname"
echo "$HOSTNAME" | sudo tee "$MNT_ROOT/etc/hostname" >/dev/null
if grep -q '^127.0.1.1' "$MNT_ROOT/etc/hosts"; then
  sudo sed -i "s/^127.0.1.1.*/127.0.1.1\t${HOSTNAME}/" "$MNT_ROOT/etc/hosts"
else
  echo -e "127.0.1.1\t${HOSTNAME}" | sudo tee -a "$MNT_ROOT/etc/hosts" >/dev/null
fi

# --- SSH key ---
log "Installing SSH public key"
SSH_DIR="$MNT_ROOT/home/${USER_NAME}/.ssh"
sudo mkdir -p "$SSH_DIR"
echo "$SSH_PUB_KEY" | sudo tee "$SSH_DIR/authorized_keys" >/dev/null
sudo chmod 700 "$SSH_DIR"
sudo chmod 600 "$SSH_DIR/authorized_keys"
sudo chown -R 1000:1000 "$MNT_ROOT/home/${USER_NAME}"

sudo chown -R 1000:1000 "$MNT_ROOT/home/${USER_NAME}"

# --- Copy Setup Files to SSD ---
log "Copying setup context to NVMe host"
TARGET_HOME="$MNT_ROOT/home/${USER_NAME}"
# Create a folder for the setup
DEST_DIR="$TARGET_HOME/silvasonic_leaflistener"
sudo mkdir -p "$DEST_DIR"

# We try to copy 'setup' and 'tools' directories.
# Determine REPO_ROOT context
if [[ -d "$SCRIPT_DIR/setup" ]]; then
    # We are on the stick (flattened root with setup/ child)
    REPO_ROOT="$SCRIPT_DIR"
else
    # We are in setup/bootstrap/, so repo root is ../..
    REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

if [[ -d "$REPO_ROOT/setup" ]]; then
    log "Copying setup/..."
    sudo cp -r "$REPO_ROOT/setup" "$DEST_DIR/"
fi
if [[ -d "$REPO_ROOT/scripts" ]]; then
    log "Copying scripts/..."
    sudo cp -r "$REPO_ROOT/scripts" "$DEST_DIR/"
fi

# Ensure config is there (if it was separate or in config/)
if [[ -f "$CONFIG_FILE" ]]; then
    # Ensure it's in the right place in the destination
    sudo mkdir -p "$DEST_DIR/setup/config"
    sudo cp "$CONFIG_FILE" "$DEST_DIR/setup/config/config.env"
fi

sudo chown -R 1000:1000 "$DEST_DIR"

log "Base image provisioning complete"

echo
echo "================================================="
echo "DONE"
echo "sudo poweroff"
echo "→ Remove Boot Stick (SD/USB)"
echo "→ Boot from NVMe"
echo "→ Connect via Ethernet or configure WiFi via Ansible"
echo "================================================="
