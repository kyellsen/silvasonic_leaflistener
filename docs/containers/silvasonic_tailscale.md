

# Container Spec: silvasonic_tailscale

> **Rolle:** Secure Overlay Network für Remote Access.
> **Tier:** Tier 0 (Vital) – Zugangssicherung.

## 1. Executive Summary
* **Problem:** Sicherer Zugriff auf das Dashboard und SSH von außen, ohne offene Ports am Router.
* **Lösung:** Tailscale VPN Client bindet das Gerät in ein privates Mesh-Netzwerk ein.

## 2. Technische Spezifikation (Docker/Podman)
Diese Werte sind verbindlich für die Implementierung.

| Parameter | Wert | Begründung/Details |
| :--- | :--- | :--- |
| **Base Image** | `tailscale/tailscale:latest` | Offizielles Image. |
| **Security Context** | `Rootless` vs `Privileged` | Benötigt oft `CAP_NET_ADMIN` und `/dev/net/tun`. Auf Pi evtl. einfacher via Host-Install, aber als Container möglich. Wir versuchen Rootless mit Device-Passthrough oder `privileged` (Ausnahme für Networking). **Entscheidung:** `Privileged` für Networking meist nötig, oder Host-Mode. Check `operational/tailscale.md`. Wir nehmen `network_mode: host` + `privileged` (Infrastructure Ausnahme). |
| **Restart Policy** | `always` | Zugriff muss garantiert sein. |
| **Ports** | `None` | (Network Host Mode). |
| **Volumes** | - `tailscale_state:/var/lib/tailscale` | State Storage (Node Identity). |
| **Dependencies** | `None`. | |

## 3. Interfaces & Datenfluss
* **Input/Output:** VPN Tunnel Traffic.

## 4. Konfiguration (Environment Variables)
*   `TS_AUTHKEY`: Auth Key (Ephemeral oder Persistent).
*   `TS_HOSTNAME`: `silvasonic-v2`.
*   `TS_STATE_DIR`: `/var/lib/tailscale`.

## 5. Abgrenzung (Out of Scope)
*   Kein lokaler Router.

## 6. Architecture & Code Best Practices
*   **Userspace Networking:** Wenn möglich nutzen.
*   **Healthcheck:** `tailscale status`.

## 7. Kritische Analyse
*   **Alternativen:** Cloudflare Tunnel, Wireguard native. Tailscale ist am einfachsten ("It just works").
