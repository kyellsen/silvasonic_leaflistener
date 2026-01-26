# Silvasonic

**Comprehensive Bioacoustic Recording Station for Long-term Monitoring**

Silvasonic is a robust, autonomous bioacoustic monitoring device built on the Raspberry Pi 5 platform. Designed for long-term deployment (3+ years), it captures the entire soundscape—from singing birds to ultrasonic bat calls—ensuring data resilience and seamless synchronization with central servers.

Status: **Active Development**

## 🚀 Quick Links

| Goal                        | Resource                                                                                                   |
| :-------------------------- | :--------------------------------------------------------------------------------------------------------- |
| **I want to build one**     | 👉 **[Getting Started Guide](docs/getting_started.md)**                                                    |
| **I want to contribute**    | 💻 **[Developer Guide](docs/development.md)** <br> ⚡ **[Native Podman Setup](docs/native_podman_dev.md)** |
| **I want to understand it** | 🏗️ **[Architecture Overview](docs/architecture/containers.md)**                                            |

---

## 💡 What is it?

Silvasonic transforms a Raspberry Pi 5 into a professional-grade acoustic recorder ("Recorder") and analyzer ("BirdNET").

**Key Capabilities:**

- **Recorder**: Uninterrupted audio recording (Ultrasonic capable).
- **Uploader**: Resilient upload/sync to cloud (Nextcloud, S3).
- **BirdNET**: On-device analysis (BirdNET) for species classification.
- **Dashboard**: Interactive local Dashboard.

> [!NOTE]
> This project follows strict "Agents & Automation" rules defined in **[AGENTS.md](AGENTS.md)**.

## ⚖️ License

This project is licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License (CC BY-NC-SA 4.0)**.
