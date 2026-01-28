# Architektur-Audit: IAM & Network Connectivity Strategy

**Status**: DRAFT  
**Datum**: 28.01.2026  
**Autor**: Lead IoT Security Architect  

## Executive Summary
Das Analysesystem "Silvasonic" setzt auf eine containerisierte Architektur auf Edge-Devices (Raspberry Pi). Die aktuelle Untersuchung bewertet die Sicherheitsarchitektur hinsichtlich Benutzerverwaltung (IAM) und Netzwerkzugriff.

**Kern-Erkenntnis**: Das System benötigt **keine** komplexe Multi-User-Verwaltung. Der Fokus muss auf "Secure-by-Default" Access über private Overlay-Netzwerke (VPN) liegen, statt das Gerät im öffentlichen Internet zu härten.

---

## Dimension 1: Local IAM & User Management

### Status Quo
- **Implementierung**: Single-User "Admin" via Environment Variables (`DASHBOARD_USER`, `DASHBOARD_PASS`).
- **Speicher**: Plaintext im `podman-compose.yml` bzw. `.env` file.
- **Datenbank**: Keine `users`-Tabelle vorhanden (Gut!).

### Analyse
1.  **Sinnhaftigkeits-Prüfung**: Ein Feldgerät ist ein "Appliance". Es gibt physisch nur einen logischen Eigentümer (den Forscher/Admin). Eine Rechteverwaltung (Role-Based Access Control - RBAC) auf dem Gerät selbst wäre massives "Over-Engineering". Sie erhöht die Komplexität und Wartungslast drastisch (Passwort-Reset-Flows, Datenbank-Migartionen, Session-Management), ohne echten Sicherheitsgewinn für ein physisch zugängliches Gerät.
2.  **Implementation & Storage**: Die Speicherung von Credentials in Environment-Variablen ist für Container akzeptabel, aber `DASHBOARD_PASS=1234` als Default ist ein **Critical Risk**.
    *   *Empfehlung*: Beim ersten Boot muss ein zufälliges Passwort generiert und in eine persistente Config geschrieben werden (oder der Start verweigert werden, bis ein Passwort gesetzt ist).
3.  **Auth-Location**: Da das Gerät oft "autark" im LAN läuft, ist eine Basis-Authentifizierung (`auth.py`) im Dashboard-Container notwendig, um unbefugten Zugriff im lokalen Netzwerk (z.B. Uni-WLAN) zu verhindern. Offloading an ein Gateway ist nur bei größeren Deployments sinnvoll.

### Empfehlung
Beibehalten des **Single-Admin Modells**. Keine Datenbank-User einführen. Fokus auf starke, rotierbare Tokens/Passwörter via Config-File.

---

## Dimension 2: Remote Access & Fleet Connectivity

### Status Quo
- **Zugriff**: SSH (Port 22) und HTTP (Port 8080) direkt exponiert.
- **Problem**: In 4G/Starlink-Netzen (CGNAT) ist das Gerät von außen nicht erreichbar ("No Inbound Traffic").

### Analyse (NAT-Traversal Strategie)
Es gibt drei Hauptwege für den Zugriff hinter NAT:
1.  **Port Forwarding / DynDNS**: Veraltet, unsicher, oft technisch unmöglich (CGNAT).
2.  **Reverse SSH Tunneling**: Erfordert einen Public Server (Bastion Host), manuelles Key-Management, instabile Verbindungen, keine UDP-Unterstützung für Audio-Streaming.
3.  **Overlay VPN (Tailscale/Zerotier)**: State-of-the-Art. Baut verschlüsselte P2P-Verbindungen auf (UDP Hole Punching). Erfordert keine offenen Ports am Router.

### Empfehlung
Einsatz eines **Tailscale Sidecars**. Das Gerät wählt sich automatisch in ein privates "Tailnet" ein. Entwickler greifen via MagicDNS (z.B. `http://silvasonic-pi`) auf das Dashboard zu, als stünden sie daneben.
*   *Vorteil*: SSH und Web-Zugriff sind "unsichtbar" für das öffentliche Internet.

---

## Dimension 3: Dashboard Exposure

### Status Quo
- Dashboard (`8080`), Controller (`8002`), Livesound (`8000`) binden an `0.0.0.0`.
- Potenziell volle Exposition ins Internet, wenn User Port-Forwarding aktiviert.

### Analyse
Das Web-Dashboard ist **nicht** für den öffentlichen Betrieb gehärtet (Hardening). FastAPI ist performant, aber keine Web-Application-Firewall (WAF).
*   **Attack Surface**: Ein öffentliches Dashboard zieht Bots an. Schwache Passwörter führen zur Kompromittierung des Hosts (via Container-Escapes oder gemounteten Volumes).
*   **Alternative**: Nutzung des vorhandenen `uploader` Containers. Das Gerät lädt Daten (Spektrogramme, Logs) passiv in eine Cloud (S3/Nextcloud). Der Nutzer betrachtet die Daten dort.

### Empfehlung
**"Dark Mode"**: Das Dashboard darf **niemals** direkt öffentlich erreichbar sein. Es dient nur zur _Konfiguration_ und _Live-Diagnose_ durch berechtigte Techniker (via VPN oder lokalem Hotspot). Die _Daten-Präsentation_ für Endanwender erfolgt asynchron über Cloud-Uploads.

---

## Decision Matrix & Deliverables

### 1. Decision Matrix

| Feature | Ansatz A (Leichtgewicht/Lokal) | Ansatz B (Enterprise/Cloud) | Empfehlung für Silvasonic |
| :--- | :--- | :--- | :--- |
| **User Auth** | **Single Static Token / Basic Auth** <br> *(Einfach, robust, kein DB-State)* | Multi-User DB mit RBAC & Sessions <br> *(Komplex, Wartungsaufwand)* | **Ansatz A** <br> (Erweitert um Random-Default-Passwort) |
| **Remote Access** | **VPN Sidecar (Tailscale)** <br> *(Secure, NAT-Traversal, Zero-Config)* | Public IP / Port Forwarding / Reverse SSH <br> *(Unsicher oder instabil)* | **Ansatz A** <br> (Tailscale im Userspace-Modus via Container) |
| **Dashboard** | **LAN/VPN only ("Dark")** <br> *(Sicher, Zugriff nur für Admins)* | Public Exposure mit SSL/Nginx <br> *(Hohes Angriffsrisiko, unnötig)* | **Ansatz A** <br> (Trennung: Config lokal, Daten in der Cloud) |

### 2. Recommended Connectivity Stack

Das Ziel ist ein Zero-Trust Netzwerkstack, der ohne offene Inbound-Ports auskommt.

#### Missing Components
1.  **Tailscale Sidecar**: Ein Container, der das gesamte Podman-Netzwerk ins VPN bridgt (oder als `network_mode: service:tailscale` für Apps dient).
2.  **Reverse Proxy (Optional)**: Caddy oder Nginx **innerhalb** des VPNs, um SSL-Zertifikate (für HTTPS) bereitzustellen und Ports unter einer Domain (z.B. `silvasonic.int`) zu bündeln, statt `IP:8080` nutzen zu müssen.

#### The "Happy Path" (User Story)

1.  **Deployment**: Der Forscher flasht das Image. Im Config-File (SD-Card) hinterlegt er einmalig einen `TAILSCALE_AUTH_KEY`.
2.  **Boot**: Silvasonic startet, der Tailscale-Container verbindet das Gerät mit dem Account des Forschers.
3.  **Access @ Home**: Der Forscher sitzt zuhause. Er öffnet `http://silvasonic-01` im Browser. Die Verbindung läuft verschlüsselt durch den VPN-Tunnel. Er loggt sich mit den lokalen Admin-Daten ein.
4.  **Security**: Ein Port-Scan auf die öffentliche IP des 4G-Routers zeigt: **Alle Ports geschlossen**.

#### Stack Skizze (podman-compose)

```yaml
services:
  tailscale:
    image: tailscale/tailscale:latest
    network_mode: host # Zugriff auf Host für SSH, oder Userspace Networking
    environment:
      - TS_AUTHKEY=${TS_KEY}
      - TS_HOSTNAME=silvasonic-field-unit
    volumes:
      - ts_state:/var/lib/tailscale

  dashboard:
    # ...
    # Dashboard ist nur via Tailscale IP oder LAN IP erreichbar
    # Keine Public Ports am Router notwendig!
```
