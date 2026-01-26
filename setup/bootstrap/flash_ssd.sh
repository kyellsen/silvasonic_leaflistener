#!/usr/bin/env bash
set -euo pipefail

# ===================== LOGGING =====================
# ANSI Color Codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
nc='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${nc} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${nc} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${nc} $1" >&2
}

die() {
    log_error "$1"
    exit 1
}

confirm() {
    local message="$1"
    while true; do
        read -r -p "${message} [y/N]: " yn
        case $yn in
            [Yy]* ) break;;
            [Nn]* | "" ) log_info "Operation aborted by user."; exit 1;;
            * ) echo "Please answer yes or no.";;
        esac
    done
}

check_dependency() {
    if ! command -v "$1" &> /dev/null; then
        die "Missing required dependency: $1"
    fi
}

# ===================== LOCATE CONFIG =====================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Try standard repo location
CONFIG_FILE="$SCRIPT_DIR/../config/bootstrap.env"

if [[ ! -f "$CONFIG_FILE" ]]; then
    # 2. Try location on stick (setup/config/bootstrap.env relative to ~/setup_files/flash_ssd.sh)
    if [[ -f "$SCRIPT_DIR/setup/config/bootstrap.env" ]]; then
        CONFIG_FILE="$SCRIPT_DIR/setup/config/bootstrap.env"
    elif [[ -f "$SCRIPT_DIR/bootstrap.env" ]]; then
        # Flattened structure: bootstrap.env next to flash_ssd.sh
        CONFIG_FILE="$SCRIPT_DIR/bootstrap.env"
    else
        log_error "Config file not found."
        log_error "Checked: $SCRIPT_DIR/../config/bootstrap.env"
        log_error "Checked: $SCRIPT_DIR/setup/config/bootstrap.env"
        log_error "Checked: $SCRIPT_DIR/bootstrap.env"
        exit 1
    fi
fi

source "$CONFIG_FILE"

MNT_BOOT="/mnt/nvme_boot"
MNT_ROOT="/mnt/nvme_root"

# ===================== VALIDATE CONFIG & ENV =====================
# Check dependencies
check_dependency "xz"
check_dependency "dd"
check_dependency "partprobe"
check_dependency "sudo"

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
         die "Image file not found: $IMAGE_FILE"
    fi
fi

# Safety check: Verify TARGET_DISK exists
if [[ ! -b "$TARGET_DISK" ]]; then
    die "Target disk '$TARGET_DISK' is not a valid block device."
fi

# Safety check: rudimentary check to avoid flashing the boot device if likely
# (This is heuristic; assumes / is mounted on the boot device)
CURRENT_ROOT_DEV=$(findmnt -n -o SOURCE /)
if [[ "$CURRENT_ROOT_DEV" == "$TARGET_DISK"* ]]; then
     log_warn "WARNING: It looks like you are trying to flash the current root device ($CURRENT_ROOT_DEV matching $TARGET_DISK)."
     confirm "Are you ABSOLUTELY sure you want to proceed? This will likely crash the system immediately."
fi


cleanup() {
  if mountpoint -q "$MNT_BOOT"; then sudo umount "$MNT_BOOT"; fi
  if mountpoint -q "$MNT_ROOT"; then sudo umount "$MNT_ROOT"; fi
}
trap cleanup EXIT

# ===================== START ======================
echo "================================================="
log_info "Silvasonic NVMe Flasher"
echo "================================================="
log_info "Host:        ${HOSTNAME}"
log_info "Target Disk: ${TARGET_DISK}"
log_info "Image:       ${IMAGE_FILE}"
echo ""

log_warn "This operation will COMPLETELY ERASE all data on ${TARGET_DISK}."
confirm "Do you want to continue?"

# --- Flash image ---
log_info "Writing image to NVMe..."
# Using status=progress for feedback. check for pipe failure via PIPESTATUS if needed, 
# but 'set -o pipefail' handles the pipeline exit code.
if ! xz -d -c "$IMAGE_FILE" | sudo dd of="$TARGET_DISK" bs=4M status=progress conv=fsync; then
    die "Flashing failed at dd step."
fi

log_info "Updating partition table..."
sudo partprobe "$TARGET_DISK"
sleep 5 # Give kernel time to update partition table

# --- Mount partitions ---
log_info "Mounting partitions..."
sudo mkdir -p "$MNT_BOOT" "$MNT_ROOT"

# Ensure partitions exist before mounting
if [[ ! -e "${TARGET_DISK}p1" ]] || [[ ! -e "${TARGET_DISK}p2" ]]; then
    die "Partitions p1/p2 not found on ${TARGET_DISK} after flashing."
fi

sudo mount "${TARGET_DISK}p1" "$MNT_BOOT"
sudo mount "${TARGET_DISK}p2" "$MNT_ROOT"

# --- User + SSH (boot mechanism) ---
log_info "Provisioning user '${USER_NAME}' and enabling SSH..."
echo "${USER_NAME}:${USER_PASSWORD_HASH}" | sudo tee "$MNT_BOOT/userconf.txt" >/dev/null
sudo touch "$MNT_BOOT/ssh"

# --- PCIe Gen 3 Enforce ---
# Für maximale NVMe Performance ab dem ersten Boot
if ! grep -q "dtparam=pciex1_gen=3" "$MNT_BOOT/config.txt"; then
    log_info "Enabling PCIe Gen 3 in config.txt"
    echo "dtparam=pciex1_gen=3" | sudo tee -a "$MNT_BOOT/config.txt"
fi

# --- Hostname ---
log_info "Setting hostname to '${HOSTNAME}'..."
echo "$HOSTNAME" | sudo tee "$MNT_ROOT/etc/hostname" >/dev/null
if grep -q '^127.0.1.1' "$MNT_ROOT/etc/hosts"; then
  sudo sed -i "s/^127.0.1.1.*/127.0.1.1\t${HOSTNAME}/" "$MNT_ROOT/etc/hosts"
else
  echo -e "127.0.1.1\t${HOSTNAME}" | sudo tee -a "$MNT_ROOT/etc/hosts" >/dev/null
fi

# --- SSH key ---
log_info "Installing SSH public key..."
SSH_DIR="$MNT_ROOT/home/${USER_NAME}/.ssh"
sudo mkdir -p "$SSH_DIR"
echo "$SSH_PUB_KEY" | sudo tee "$SSH_DIR/authorized_keys" >/dev/null
sudo chmod 700 "$SSH_DIR"
sudo chmod 600 "$SSH_DIR/authorized_keys"
sudo chown -R 1000:1000 "$MNT_ROOT/home/${USER_NAME}"

# --- NOTE: NO REPO COPYING ---
# The repository is cloned via Ansible (install.sh) from GitHub.
# This keeps the SD/USB stick minimal and ensures the Pi always gets the latest code.

log_info "Base image provisioning complete."

echo
echo "================================================="
echo -e "${GREEN}DONE - NVMe is ready for boot!${nc}"
echo "================================================="
echo ""
echo "Next steps:"
echo "  1. sudo poweroff"
echo "  2. Remove Boot Stick (SD/USB)"
echo "  3. Boot from NVMe"
echo "  4. From WORKSTATION, run: ./setup/install.sh"
echo "     (This will clone the repo from GitHub + provision the Pi)"
echo "================================================="
