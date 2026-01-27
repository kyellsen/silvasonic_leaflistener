#!/usr/bin/env bash
set -e

# ===================== SETUP & CONFIG =====================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOOTSTRAP_FILE="$SCRIPT_DIR/config/bootstrap.env"

if [[ ! -f "$BOOTSTRAP_FILE" ]]; then
    # Fallback to local if flattened
    if [[ -f "$SCRIPT_DIR/bootstrap.env" ]]; then
        BOOTSTRAP_FILE="$SCRIPT_DIR/bootstrap.env"
    else
        echo "WARNING: Bootstrap config not found ($BOOTSTRAP_FILE). Installation might rely on defaults."
    fi
fi

echo "Loading configuration from $BOOTSTRAP_FILE..."
source "$BOOTSTRAP_FILE"

# ===================== WORKSTATION-ONLY CHECK =====================
# This script MUST run from workstation, not on the Pi!
if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null || [[ -f /usr/bin/raspi-config ]]; then
    echo "=============================================="
    echo "ERROR: This script runs from your WORKSTATION!"
    echo "=============================================="
    echo ""
    echo "Do NOT run this on the Raspberry Pi."
    echo "Run it from your development machine via SSH."
    echo ""
    echo "Usage: ./setup/install.sh"
    echo "       (from your workstation, connects via SSH to the Pi)"
    exit 1
fi

# ===================== PRE-FLIGHT CHECKS =====================
# Default to silvasonic.local if not set in config
TARGET="${SSH_TARGET:-silvasonic.local}"
echo "Target: $TARGET"

# WARN/BLOCK if running as root on workstation
# Root check removed - we explicitly support running as root now.
# Note: If running as root, ensure your SSH keys are available to the root user.

# Check if we can reach the target using SSH (resolves aliases)
echo "Checking connectivity to '$TARGET'..."
if ! ssh -q -o BatchMode=yes -o ConnectTimeout=5 "$TARGET" exit; then
    echo "ERROR: Cannot connect to '$TARGET' via SSH." 
    echo "Please check:"
    echo "1. The Pi is booted and on the network."
    echo "2. You have configured access in ~/.ssh/config (if using alias)."
    echo "3. You are NOT running with sudo (which hides your config)."
    exit 1
fi

# Ensure Ansible is available
if ! command -v ansible &> /dev/null; then
    echo "ERROR: Ansible is not installed on your workstation."
    echo "Please install it:"
    echo "  - Fedora: sudo dnf install ansible"
    echo "  - Ubuntu: sudo apt install ansible"
    echo "  - macOS:  brew install ansible"
    exit 1
fi

# ===================== RUN ANSIBLE =====================
echo "Running Ansible Provisioning via SSH to '$TARGET'..."

# Remote execution via SSH
# ansible_host = $TARGET (can be IP, hostname, or SSH alias)
# ansible_connection = ssh
CONN_ARGS_SSH="$TARGET"
CONN_ARGS="-e ansible_host=$TARGET -e ansible_connection=ssh"

ansible-playbook "$SCRIPT_DIR/provision/main.yml" \
    -i "$SCRIPT_DIR/provision/inventory.yml" \
    -e "wifi_ssid=$WIFI_SSID" \
    -e "wifi_psk=$WIFI_PSK" \
    -e "wifi_country=$WIFI_COUNTRY" \
    -e "user=$USER_NAME" \
    -e "local_repo_root=$(dirname "$SCRIPT_DIR")" \
    $CONN_ARGS

echo "=========================================="
echo "Phase 2: Building Images (Logging enabled)"
echo "This may take a while (10-20 min) on a Pi..."
echo "=========================================="

REPO_DEST="/mnt/data/dev/silvasonic"

# Explicitly build images (streaming output)
ssh -t $CONN_ARGS_SSH "cd $REPO_DEST && sudo podman-compose build"

echo "=========================================="
echo "Phase 3: Starting Service"
echo "=========================================="

# Restart service (picks up new images)
ssh -t $CONN_ARGS_SSH "sudo systemctl enable --now silvasonic && sudo systemctl restart silvasonic"


echo "=========================================="
echo "Setup Complete!"
echo "You may check logs with: ssh $TARGET 'journalctl -fu silvasonic'"
echo "=========================================="
