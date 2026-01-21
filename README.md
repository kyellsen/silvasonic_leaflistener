# Silvasonic Leaflistener

**Comprehensive Bioacoustic Recording Station for Long-term Monitoring**

Silvasonic Leaflistener is a robust, autonomous bioacoustic monitoring device built on the Raspberry Pi 5 platform. Designed for long-term deployment (3+ years), it captures the entire soundscape—from singing birds to ultrasonic bat calls—ensuring data resilience and seamless synchronization with central servers.

> [!IMPORTANT]
> **MVP Scope Definition**
> The current development phase focuses strictly on:
>
> 1.  **Infrastructure**: Automated setup & OS hardening.
> 2.  **The Ear**: Reliable, uninterrupted audio capture with auto-detecting microphone profiles.
> 3.  **The Carrier**: Resilient data synchronization.
>
> _Advanced analysis, on-device ML, and complex dashboards are explicitly OUT OF SCOPE for this phase._

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
- **Edge Intelligence**: On-device buffering and optional initial analysis (ML) to ensure data integrity even without network.

## Hardware Specifications

The system is built on the Raspberry Pi 5 platform with NVMe storage and high-fidelity ultrasonic microphones.

[View Hardware Specifications](docs/hardware.md)

## Architecture Overview

Silvasonic uses a containerized "Mirror Infrastructure" ensuring that audio capture ("The Ear") is isolated from uploads ("The Carrier") and UI ("The Face").

[View Container Strategy](docs/containers.md)
[View Data Flow & Storage](docs/data_flow.md)

## Setup & Installation

The setup process is fully automated.

[Go to Setup Guide](setup/README.md)

## Contributing & Agents

All contributors (human and AI) must follow the strict rules defined in our agent guidelines.

[Read AGENTS.md](AGENTS.md)

## Development

[View Development Workflow](docs/dev_workflow.md)
