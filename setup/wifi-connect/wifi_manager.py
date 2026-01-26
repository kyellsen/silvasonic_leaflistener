import logging
import subprocess

logger = logging.getLogger("wifi_manager")

class WifiManager:
    """Manage WiFi connections and Access Point mode."""
    AP_SSID = "Silvasonic-Setup"
    AP_IP = "10.0.0.1"
    INTERFACE = "wlan0"

    @staticmethod
    def run_command(cmd):
        """Execute a shell command and return the output."""
        try:
            result = subprocess.run(
                cmd, shell=True, check=True, capture_output=True, text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {cmd}\nError: {e.stderr}")
            return None

    def is_connected(self):
        """Check if we have an active connection to the internet (or just local router)."""
        # Simple check: do we have an active connection that is NOT our AP?
        cmd = "nmcli -t -f TYPE,STATE,CONNECTION device"
        output = self.run_command(cmd)
        if output:
            for line in output.split('\n'):
                # e.g. wifi:connected:MyHomeWiFi
                parts = line.split(':')
                if len(parts) >= 3:
                    dtype, state, conn = parts[0], parts[1], parts[2]
                    if dtype == "wifi" and state == "connected":
                        if conn == self.AP_SSID:
                            continue # We are connected to our own AP
                        return True
                    if dtype == "ethernet" and state == "connected":
                        return True
        return False

    def scan_networks(self):
        """Return list of available SSIDs."""
        cmd = "nmcli -t -f SSID,SIGNAL,SECURITY dev wifi list --rescan yes"
        output = self.run_command(cmd)
        networks = []
        seen = set()
        if output:
            for line in output.split('\n'):
                # Format: SSID:SIGNAL:SECURITY
                # Note: SSID might be empty for hidden networks
                parts = line.split(':')
                if len(parts) >= 1:
                    ssid = parts[0]
                    if not ssid or ssid in seen:
                        continue
                    # Clean up escaping if any (nmcli sometimes escapes colons)
                    ssid = ssid.replace('\\:', ':')
                    seen.add(ssid)

                    signal = 0
                    if len(parts) >= 2 and parts[1].isdigit():
                        signal = int(parts[1])

                    security = parts[2] if len(parts) >= 3 else ""

                    networks.append({
                        "ssid": ssid,
                        "signal": signal,
                        "security": security
                    })
        # Sort by signal strength
        networks.sort(key=lambda x: x['signal'], reverse=True)
        return networks

    def connect_wifi(self, ssid, password):
        """Attempt to connect to a network. Deletes old connection if exists."""
        logger.info(f"Attempting to connect to {ssid}")

        # Delete existing connection profile if it exists to avoid duplicates
        self.run_command(f"nmcli connection delete id '{ssid}'")

        cmd = f"nmcli dev wifi connect '{ssid}' password '{password}'"
        if not password:
             cmd = f"nmcli dev wifi connect '{ssid}'"

        result = self.run_command(cmd)
        if result:
            logger.info(f"Successfully connected to {ssid}")
            return True
        return False

    def start_ap(self):
        """Start the Access Point."""
        logger.info("Starting Access Point...")
        # Check if AP connection exists
        check = self.run_command(f"nmcli connection show '{self.AP_SSID}'")
        if not check:
            # Create it
            # auto-connect=no because we want to control when it starts usually,
            # but for this script we might want manual control.
            cmd = (
                f"nmcli con add type wifi ifname {self.INTERFACE} con-name '{self.AP_SSID}' "
                f"ssid '{self.AP_SSID}' mode ap ipv4.method shared ipv4.addresses {self.AP_IP}/24 "
                "wifi-sec.key-mgmt wpa-psk wifi-sec.psk 'silvasonic'"
            )
            # Default password 'silvasonic' to modify if needed
            self.run_command(cmd)

        # Activate it
        self.run_command(f"nmcli connection up '{self.AP_SSID}'")

    def is_ap_running(self):
        """Check if the Access Point is currently active."""
        # List active connections and look for our SSID
        cmd = "nmcli -t -f NAME connection show --active"
        output = self.run_command(cmd)
        if output:
            for line in output.split('\n'):
                if line.strip() == self.AP_SSID:
                    return True
        return False
