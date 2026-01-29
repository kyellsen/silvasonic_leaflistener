# Container: silvasonic_tailscale

## 1. Das Problem / Die Lücke
Der Zugriff auf das System von außerhalb des lokalen Netzwerks erfordert normalerweise Port-Forwarding am Router, was Sicherheitsrisiken birgt und bei CGNAT (Mobilfunk/Starlink) oft unmöglich ist.

## 2. Nutzen für den User
*   **Remote Access**: Zugriff auf das Dashboard von überall auf der Welt, sicher und verschlüsselt.
*   **Zero Config**: Keine Router-Konfiguration notwendig.
*   **Sicherheit**: Das Device ist nicht im öffentlichen Internet exponiert.

## 3. Kernaufgaben (Core Responsibilities)
*   **Inputs**:
    *   Auth-Key (initial) zur Registrierung im Tailnet.
    *   Verschlüsselter WireGuard-Traffix via UDP.
*   **Processing**:
    *   Aufbau eines Mesh-VPN Tunnels.
    *   Routing von Traffic aus dem Tailnet an lokale Services.
*   **Outputs**:
    *   Netzwerk-Verbindung zu `silvasonic_gateway` oder `silvasonic_dashboard`.

## 4. Abgrenzung (Out of Scope)
*   **Kein öffentlicher Server**: Macht den Dienst nicht "public" für jedermann, nur für authentifizierte Tailnet-User.
*   **User Management**: Verwaltet keine User (passiert bei Tailscale.com).

## 5. Technologien die dieser Container nutzt
*   **Basis-Image**: `tailscale/tailscale:latest`
*   **Wichtige Komponenten**:
    *   Tailscale Daemon (tailscaled)
    *   Userspace Networking (tun/tap)

## 6. Kritische Punkte
*   **Auth Key Expiry**: Keys laufen ab. Um persistenten Zugang zu sichern, muss das Device im Admin-Panel als "No Expiry" markiert werden oder OAuth Flow genutzt werden (im Container schwieriger).
*   **State Persistence**: Der Ordner `/var/lib/tailscale` MUSS persistiert sein (Volume), sonst generiert der Container bei jedem Neustart eine neue IP/Identität.
