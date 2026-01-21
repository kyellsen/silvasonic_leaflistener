# Hardware Specifications

## Core Components

### Single Board Computer (SBC)

- **Model**: Raspberry Pi 5
- **RAM**:
  - **Minimum**: 2GB (Sufficient for pure recording "Ear" & "Carrier" roles).
  - **Recommended**: 8GB (Required if On-device ML/Analysis is planned).

### Storage (NVMe)

Silvasonic relies on NVMe storage for high-speed buffering and reliability. SD cards are used for **boot only**.

- **Interface**: PCIe using a HAT (e.g., Pineberry, Pimoroni).
- **Capacity**:
  - **Minimum**: 128GB (Good for ~1-2 days of recording buffer).
  - **Recommended**: 512GB+ (Allows for up to 14 days of offline retention).
- **Form Factor**: M.2 2230, 2242, or 2280 (depending on chosen HAT).

### Audio Interface

- **Microphone**: **Dodotronic Ultramic384 EVO**.
- **Bandwidth**: Must support 384kHz sampling rate (192kHz bandwidth) via USB.

### Power & Enclosure

- **Power Supply**: Official 27W USB-C PSU (Permanent connection).
- **Cooling**: Active cooling (Fan) or passive metal case is **mandatory** for continuous load.

## ConnectivityRequirement

- **Network**: Ethernet (preferred) or Wi-Fi.
- **VPN**: Must allow outgoing UDP traffic for Tailscale/Wireguard.
