# Silvasonic Port Standards

This document defines the standard port allocation for the Silvasonic ecosystem to ensure consistency and avoid conflicts.

## Concept

Reference: `2026-01-28-Port-Standardization`

*   **Service APIs (TCP)**: `8000 - 8009` include internal REST APIs.
*   **Stream Ports (UDP)**: `8010 - 8049` are used for high-bandwidth audio streams.
*   **Public Interface (Gateway)**: `80` (HTTP) / `443` (HTTPS).
*   **Service APIs (Internal)**: `8000+`.
*   **Database**: `5432` (PostgreSQL Standard).

## Port Registry

| Service | Port | Protocol | Description | Env Variable |
| :--- | :--- | :--- | :--- | :--- |
| **Gateway** | `80/443` | TCP | **Public Entry Point**. | - |
| **Livesound** | `8000` | TCP / HTTP | Icecast Streaming Server (Internal) | `PORT` |
| **Dashboard** | `8000` | TCP / HTTP | Web Interface (Internal) | `DASHBOARD_PORT` |
| **Uploader** | `8001` | TCP / HTTP | Internal REST API | `PORT` |
| **Database** | `5432` | TCP | PostgreSQL Database | `POSTGRES_PORT` |

## Configuration Guidelines

### Environment Variables
*   **APIs**: Use `HOST` (0.0.0.0) and `PORT` (int).
*   **Streams**: Use specific variables like `LIVE_STREAM_PORT` or mapping dicts like `LISTEN_PORTS`.

### Docker / Podman
*   Containers should expose these ports internally.
*   `podman-compose.yml` maps them 1:1 to the host to allow easy debugging and access.
