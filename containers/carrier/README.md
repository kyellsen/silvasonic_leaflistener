# The Carrier

The **Carrier** is responsible for reliably synchronizing recorded audio files from the edge device to the central server.

## Technology

It uses **[Syncthing](https://syncthing.net/)**, a continuous file synchronization program.

- **Image**: `syncthing/syncthing:latest`
- **Role**: "Send Only" (conceptually, though configured via GUI).
- **Architecture**:
  - The carrier has **Read-Only** access to the recording directory (`/mnt/data/services/silvasonic/recordings`).
  - It maintains its own internal database and config in `/mnt/data/containers/carrier/config`.

## Configuration

1. **Access GUI**:
   - URL: `http://<device-ip>:8384`
   - Default User/Pass: None (Syncthing warns you to set one).

2. **Folder Setup**:
   - The recording folder is mapped to inside the container at: `/var/syncthing/data/raw`.
   - Add this folder in the GUI and share it with the central server device.

## Why Syncthing?

- **Resilience**: Handles intermittent connectivity gracefully.
- **P2P**: Doesn't require a static IP on the server if using global discovery (or can use local discovery over VPN).
- **Efficient**: Uses block-level transfer for large files (though less relevant for FLACs, it handles resuming well).
