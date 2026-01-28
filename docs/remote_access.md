# Remote Access Guide (Tailscale)

Silvasonic employs **Tailscale** for secure remote access. This allows you to connect to the device even when it is behind 4G/LTE NAT or Starlink, without requiring port forwarding or a public IP address.

## 1. What is Tailscale?
Tailscale is a zero-config VPN based on WireGuard®. It creates a private, encrypted mesh network between your devices.
- **No Public IP needed**: It traverses firewalls automatically.
- **Secure by Default**: No ports are opened to the public internet. Access is only possible for devices in your private Tailnet.

## 2. Setup Instructions

### Step 1: Create a Tailscale Account
1.  Go to [tailscale.com](https://tailscale.com) and sign up (Free for personal use).
2.  Install the Tailscale Client on your **Laptop/Smartphone** (the device you will control Silvasonic from).
3.  Log in to the client.

### Step 2: Generate an Auth Key
1.  Open the [Tailscale Admin Console](https://login.tailscale.com/admin/settings/keys).
2.  Go to **Settings > Keys**.
3.  Click **Generate auth key**.
    -   **Reusability**: `Reusable` (recommended if you deploy multiple devices) or `One-off`.
    -   **Tags**: Optional (e.g., `tag:server`).
4.  **Copy the key** (starting with `tskey-...`).

### Step 3: Configure Silvasonic
1.  On the Silvasonic device log in via SSH or access the SD card configuration.
2.  Open the `.env` file in the root directory.
3.  Paste your key into the `TS_AUTHKEY` variable:

```bash
# .env
TS_AUTHKEY=tskey-auth-k123456CNTRL-abcdefg1234567
HOSTNAME=silvasonic-unit-01
```

4.  Recreate the container:
    ```bash
    podman-compose up -d tailscale
    ```

## 3. Accessing the Dashboard

Once the `tailscale` container is running:

1.  Open your browser on your Laptop (which must be connected to Tailscale).
2.  Navigate to:
    -   `http://silvasonic-unit-01:8080` (Replace with your chosen `HOSTNAME`)
    -   Alternatively, check the Tailscale Admin Console for the device's **MagicDNS** name or **Tailscale IP** (e.g., `100.x.y.z`).

## 4. Troubleshooting

**Check Status**:
```bash
podman logs silvasonic_tailscale
```

**Verify Connection**:
```bash
podman exec silvasonic_tailscale tailscale status
```

**DNS Issues**:
If `http://silvasonic-unit-01` does not resolve, ensure "MagicDNS" is enabled in your Tailscale Admin Console. Otherwise, use the IP address (e.g., `http://100.101.102.103:8080`).
