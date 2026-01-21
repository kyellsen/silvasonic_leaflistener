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

# ===================== ENVIRONMENT DETECTION =====================
IS_RASPI=false
if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null || [[ -f /usr/bin/raspi-config ]]; then
    IS_RASPI=true
fi

# ===================== PRE-FLIGHT CHECKS =====================
if [[ "$IS_RASPI" == "true" ]]; then
    # Local execution on Pi requires Ansible + Root/Sudo implies passwordless or ask pass
    if [[ $EUID -ne 0 ]]; then
       echo "Running locally on Pi: Please run as root (sudo)." 
       exit 1
    fi
else
    echo "Detected execution on Workstation (Not a Raspberry Pi)."
    
    # WARN/BLOCK if running as root on workstation
    if [[ $EUID -eq 0 ]]; then
        echo "WARNING: You are running as root (sudo)."
        echo "This means your personal SSH config (~/.ssh/config) will likely be IGNORED."
        echo "If you use SSH aliases like '$SSH_TARGET', please run this script WITHOUT sudo."
        echo "(Ansible will ask for become/sudo passwords on the target if needed)."
        read -p "Continue anyway? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Default to silvasonic.local if not set in config
    TARGET="${SSH_TARGET:-silvasonic.local}"
    echo "--> Switching to REMOTE provisioning mode targeting '$TARGET'."
    
    # Check if we can reach the target using SSH (resolves aliases)
    # plain ping fails on ssh aliases
    echo "Checking connectivity to '$TARGET'..."
    if ! ssh -q -o BatchMode=yes -o ConnectTimeout=5 "$TARGET" exit; then
        echo "ERROR: Cannot connect to '$TARGET' via SSH." 
        echo "Please check:"
        echo "1. The Pi is booted."
        echo "2. You have configured access in ~/.ssh/config (if using alias)."
        echo "3. You are NOT running with sudo (which hides your config)."
        exit 1
    fi
fi

# Ensure Ansible is availalble
if ! command -v ansible &> /dev/null; then
    echo "ERROR: Ansible is not installed. Please install it manually for your OS."
    exit 1
fi

# ===================== RUN ANSIBLE =====================
echo "Running Ansible Provisioning..."

# Define Connection Params
if [[ "$IS_RASPI" == "true" ]]; then
    CONN_ARGS="-e ansible_host=localhost -e ansible_connection=local"
else
    # Remote execution
    # Use the target from config (e.g. 'sse', 'raspi5', or '192.168.x.x')
    TARGET="${SSH_TARGET:-silvasonic.local}"
    
    # We set ansible_host to the target. 
    # If the user has an ssh_config alias (like 'sse'), ansible_host=sse works perfectly with ansible_connection=ssh.
    # We DO NOT set ansible_user here blindly if using a custom host, because the ssh config might specify 'User pi'.
    # However, our playbook expects 'user' variable for creating folders/permissions.
    
    # Logic:
    # 1. ansible_host = $TARGET
    # 2. ansible_user = (Ansible defaults to current user or ssh config user). 
    #    BUT: our playbooks might need 'become: true'.
    #    AND: we pass `-e user=$USER_NAME` to the playbook for file permissions logic.
    
    CONN_ARGS="-e ansible_host=$TARGET -e ansible_connection=ssh"
    echo "NOTE: Connecting to $TARGET. Ensure SSH access is configured."
fi

ansible-playbook "$SCRIPT_DIR/provision/main.yml" \
    -i "$SCRIPT_DIR/provision/inventory.yml" \
    -e "wifi_ssid=$WIFI_SSID" \
    -e "wifi_psk=$WIFI_PSK" \
    -e "wifi_country=$WIFI_COUNTRY" \
    -e "user=$USER_NAME" \
    $CONN_ARGS

echo "=========================================="
echo "Setup Complete!"
echo "You may need to reboot for all changes to take effect."
echo "=========================================="
