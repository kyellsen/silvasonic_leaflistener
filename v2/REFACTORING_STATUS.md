# 🏗️ Silvasonic V2 Refactoring Status

This document tracks the migration of containers to the V2 architecture (`v2/concept.md`).

| Container | Priority | Status | Owner | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Infrastructure** | | | | |
| `silvasonic_gateway` | Tier 0 | 🟢 Refactored | | Caddy Reverse Proxy |
| `silvasonic_database` | Tier 0 | 🟢 Refactored | | TimescaleDB |
| `silvasonic_redis` | Tier 0 | 🟢 Refactored | | Redis |
| `silvasonic_tailscale` | Tier 0 | 🟢 Refactored | | VPN Mesh |
| **Core Loop** | | | | |
| `silvasonic_controller` | Tier 0 |  Refactored | | Hardware Manager (Privileged) |
| `silvasonic_processor` | Tier 1 | 🟢 Refactored | | "The Brain" (Indexer/Logic) |
| `silvasonic_monitor` | Tier 0 | 🟢 Refactored | | Watchdog & Notifications |
| **Workers** | | | | |
| `silvasonic_recorder` | Tier 1 | 🟢 Refactored | | Audio Capture |
| `silvasonic_uploader` | Tier 2 | 🟢 Refactored | | Cloud Sync |
| `silvasonic_birdnet` | Tier 4 | � Refactored | | Analysis |
| `silvasonic_weather` | Tier 4 | � Refactored | | Metereology |
| **Frontend** | | | | |
| `silvasonic_dashboard` | Tier 3 | 🟡 Frozen | | **Updates skipped** in Phase 1 |
| `silvasonic_livesound` | Tier 4 | � Refactored | | Streaming Relay |

## Legend
- 🔴 **Pending**: Not started.
- 🟡 **In Progress**: Currently working on it.
- 🟢 **Refactored**: Code updated to V2 spec.
- 🔵 **Verified**: Builds and runs successfully.
- ⚪ **Frozen**: Intentionally left out.
