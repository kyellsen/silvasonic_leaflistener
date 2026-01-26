# Silvasonic

**Comprehensive Bioacoustic Recording Station for Long-term Monitoring**

Silvasonic is a robust, autonomous bioacoustic monitoring device built on the Raspberry Pi 5 platform. Designed for long-term deployment (3+ years), it captures the entire soundscape—from singing birds to ultrasonic bat calls—ensuring data resilience and seamless synchronization with central servers.

> [!IMPORTANT]
> **Current Status**
> The project provides a full-stack bioacoustic station including:
>
> 1.  **The Ear**: Reliable recording.
> 2.  **The Carrier**: Resilient upload/sync.
> 3.  **The Brain**: On-device BirdNET analysis.
> 4.  **The Face**: Interactive Dashboard.

## 🚀 Inbetriebnahme

**Du hast einen neuen Raspberry Pi und willst starten?**

Hier ist die einzige Anleitung, die du brauchst:

👉 **[QUICKSTART.md](QUICKSTART.md)** 👈

_(Führt dich Schritt für Schritt vom leeren Stick bis zum laufenden System)_

---

## Supported Microphones

The recorder auto-detects USB microphones via YAML profiles:

| Microphone                   | Sample Rate | Best For       |
| ---------------------------- | ----------- | -------------- |
| Dodotronic Ultramic 384K EVO | 384 kHz     | Bats, Insects  |
| Generic USB                  | 48 kHz      | Birds, General |

Adding new microphone support is as simple as creating a YAML file! [See Deployment Guide](docs/deployment.md#contributing-microphone-profiles)

## Requirements

Ensure your hardware meets the **Raspberry Pi 5** platform standard.

[View Hardware Specifications](docs/hardware.md)

## Vision

- **Continuous Monitoring**: 24/7 recording capability for bioacoustics (birds, bats, environmental noise).
- **Resilience**: Designed to run non-stop for at least 3 years with active caching and crash recovery.
- **Scalability**: "Fleet-ready" architecture allowing quick deployment to multiple devices via automated setup scripts and Ansible.
- **Edge Intelligence**: On-device buffering and analysis (BirdNET) to ensure data integrity and immediate insights.

## Architecture Overview

Silvasonic uses a containerized "Mirror Infrastructure" ensuring that audio capture ("The Ear") is isolated from uploads ("The Carrier") and UI ("The Face").

**Active Containers:**

- **recorder**: Audio Capture
- **uploader**: Data Synchronization
- **healthchecker**: System Monitoring & Alerts
- **birdnet**: Bird Species Analysis
- **dashboard**: User Interface
- **livesound**: Specialized Acoustic Analysis (Live Streaming)
- **db**: Central Database

[View Container Strategy](docs/containers.md)
[View Data Flow & Storage](docs/data_flow.md)

## Contributing & Agents

All contributors (human and AI) must follow the strict rules defined in our agent guidelines.

[Read AGENTS.md](AGENTS.md)

## Development

[View Development Workflow](docs/dev_workflow.md)

## License

This project is licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License (CC BY-NC-SA 4.0)**.

- **Non-Commercial**: You may not use this software for commercial purposes without explicit permission.
- **Open Source**: You are free to copy, distribute, and modify the software for personal or non-commercial use.
- **ShareAlike**: If you modify and distribute this software, you must distribute your contributions under the same license.

This project includes components such as **BirdNET-Analyzer**, which are also licensed under CC BY-NC-SA 4.0.
