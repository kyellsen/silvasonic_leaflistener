#!/usr/bin/env bash
set -e

# ===================== SETUP & CONFIG =====================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/config/config.env"

if [[ ! -f "$CONFIG_FILE" ]]; then
    # Fallback to local if flattened
    if [[ -f "$SCRIPT_DIR/config.env" ]]; then
        CONFIG_FILE="$SCRIPT_DIR/config.env"
    else
        echo "ERROR: Config file not found ($CONFIG_FILE). Please copy setup/config.example.env to setup/config/config.env and edit it."
        exit 1
    fi
fi

echo "Loading configuration from $CONFIG_FILE..."
source "$CONFIG_FILE"

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
if [[ $EUID -eq 0 ]]; then
    echo "WARNING: You are running as root (sudo)."
    echo "This means your personal SSH config (~/.ssh/config) will likely be IGNORED."
    echo "If you use SSH aliases like '$TARGET', please run this script WITHOUT sudo."
    echo "(Ansible will ask for become/sudo passwords on the target if needed)."
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

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
CONN_ARGS="-e ansible_host=$TARGET -e ansible_connection=ssh"

ansible-playbook "$SCRIPT_DIR/provision/main.yml" \
    -i "$SCRIPT_DIR/provision/inventory.yml" \
    -e "wifi_ssid=$WIFI_SSID" \
    -e "wifi_psk=$WIFI_PSK" \
    -e "wifi_country=$WIFI_COUNTRY" \
    -e "user=$USER_NAME" \
    $CONN_ARGS

echo "=========================================="
echo "Setup Complete!"
echo "You may need to reboot the Pi for all changes to take effect."
echo "  ssh $TARGET 'sudo reboot'"
echo "=========================================="
