# Silvasonic

**Comprehensive Bioacoustic Recording Station for Long-term Monitoring**

Silvasonic is a robust, autonomous bioacoustic monitoring device built on the Raspberry Pi 5 platform. Designed for long-term deployment (3+ years), it captures the entire soundscape—from singing birds to ultrasonic bat calls—ensuring data resilience and seamless synchronization with central servers.

## 🚧 Project Status: MVP (Minimum Viable Product)

This project is currently in the **MVP** phase. The core infrastructure for stable recording, management, and avian analysis is complete and tested in the field. Active development is focused on expanding analysis capabilities (specifically for bats) and refining the user experience.

## 🚀 Quick Links

| Goal | Resource |
| :--- | :--- |
| **I want to build one** | 👉 **[Getting Started Guide](docs/getting_started.md)** |
| **I want to contribute** | 💻 **[Developer Guide](docs/development.md)** <br> ⚡ **[Native Podman Setup](docs/native_podman_dev.md)** |
| **I want to understand it** | 🏗️ **[Container Reference](docs/containers/)** <br> 📡 **[Data Flow](docs/architecture/data_flow.md)** |

---

## 💡 Features & Capabilities

Silvasonic transforms a Raspberry Pi 5 into a professional-grade acoustic recorder and analyzer.

### ✅ Implemented (Core MVP)

*   **Robust Recording**: Continuous or scheduled recording supporting high sample rates (up to 384kHz) for both audible and **ultrasonic** ranges (bats).
*   **Bird Analysis (BirdNET)**: Native, on-device integration of BirdNET for real-time or batched classification of avian species.
*   **Resilient Data Sync (Uploader)**: "Store & Forward" architecture ensures data is safely uploaded to cloud storage (Nextcloud, S3) without data loss, even with intermittent connectivity.
*   **System Health**: Comprehensive self-monitoring with hardware watchdogs, container health checks, and a local **Dashboard** for status visualization.

### 📅 Roadmap (Coming Soon)

*   **Bat Analysis Pipeline**: While *recording* bats is fully supported, the *analysis* and triggering logic (e.g., BatDetect) is **not yet implemented**.
*   **Advanced Triggering**: More granular frequency-based triggers for selective recording.

> [!NOTE]
> This project follows strict "Agents & Automation" rules defined in **[AGENTS.md](AGENTS.md)**.

## ⚖️ License

This project is licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License (CC BY-NC-SA 4.0)**.
