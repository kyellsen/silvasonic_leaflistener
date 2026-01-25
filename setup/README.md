# Silvasonic Setup Guide

> **Minimal SD + GitHub Clone**: Der Stick enthält nur Bootstrap-Skripte, das Repo kommt immer frisch von GitHub.

---

## Übersicht

```
┌─────────────────────────────────────────────────────────────────────────┐
│  SD-KARTE / USB-STICK (Minimal Bootstrap)                               │
│  Enthält NUR:                                                           │
│    • flash_ssd.sh   (NVMe Installer)                                    │
│    • config.env     (Credentials)                                       │
│    • OS-Image       (Raspi OS)                                          │
│  Enthält NICHT: Das Repository!                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  ANSIBLE (install.sh von Workstation)                                   │
│    • Klont Repo von GitHub                                              │
│    • Installiert Pakete                                                 │
│    • Konfiguriert Storage                                               │
└─────────────────────────────────────────────────────────────────────────┘
```

| Phase | Script             | Läuft auf         | Was passiert                            |
| ----- | ------------------ | ----------------- | --------------------------------------- |
| 1     | `prepare_stick.sh` | Workstation       | Minimalen Boot-Stick erstellen          |
| 2     | `flash_ssd.sh`     | Pi (vom Stick)    | NVMe flashen, User/SSH einrichten       |
| 3     | `install.sh`       | Workstation → SSH | **Repo klonen** + System provisionieren |

---

## Voraussetzungen

- Raspberry Pi 5 (oder 4)
- NVMe SSD + HAT
- SD-Karte oder USB-Stick (temporär)
- Workstation mit `ansible` installiert

---

## Phase 1: Boot-Stick erstellen (Workstation)

### 1.1) Konfiguration vorbereiten

```bash
cd ~/dev/silvasonic
mkdir -p setup/config
cp setup/config.example.env setup/config/config.env
nano setup/config/config.env
```

**Passwort-Hash generieren:**

```bash
echo 'dein_passwort' | openssl passwd -6 -stdin
```

### 1.2) OS-Image auf SD schreiben

Mit Raspberry Pi Imager oder beliebigem Tool:

- OS: `Raspberry Pi OS Lite (64-bit)`
- Keine OS-Customisation nötig

### 1.3) Bootstrap-Dateien hinzufügen

```bash
sudo ./setup/bootstrap/prepare_stick.sh
```

**Das kopiert nur:**

- ✅ `flash_ssd.sh`
- ✅ `config.env`
- ✅ OS-Image
- ❌ KEIN Repository!

---

## Phase 2: NVMe flashen (auf dem Pi)

### 2.1) Von SD booten

```bash
ssh pi@silvasonic.local
# Passwort: aus config.env (USER_PASSWORD_HASH)
```

### 2.2) SSD flashen

```bash
cd ~/setup_files
sudo ./flash_ssd.sh
sudo poweroff
```

**SD-Karte entfernen → Von NVMe booten**

---

## Phase 3: Provisioning (Workstation → SSH)

> [!IMPORTANT]
> Dieses Script läuft auf deiner **Workstation** und:
>
> 1. Verbindet sich via SSH zum Pi
> 2. **Klont das Repo von GitHub**
> 3. Installiert alle Pakete und konfiguriert das System

### 3.1) Install-Script ausführen

```bash
cd ~/dev/silvasonic
./setup/install.sh
```

**Was passiert:**

- System-Update
- Pakete installieren (Podman, Git, etc.)
- **Repo klonen nach `/mnt/data/dev/silvasonic`**
- Storage-Struktur anlegen
- WiFi konfigurieren (falls in config.env gesetzt)

### 3.2) Pi neustarten

```bash
ssh admin@silvasonic.local 'sudo reboot'
```

---

## Phase 4: Container starten

```bash
ssh admin@silvasonic.local
cd /mnt/data/dev/silvasonic
sudo podman-compose -f podman-compose.yml up --build -d
sudo podman logs -f silvasonic_ear
```

Mehr Details: [docs/deployment.md](../docs/deployment.md)

---

## Updates

Da das Repo von GitHub geklont wurde:

```bash
cd /mnt/data/dev/silvasonic
git pull
sudo podman-compose down
sudo podman-compose up --build -d
```

---

## Re-Provisioning

Bei Änderungen an der Infrastruktur:

```bash
# Von der Workstation
./setup/install.sh
```

Ansible ist idempotent – es werden nur Änderungen angewendet.

---

## Troubleshooting

### SSH funktioniert nicht

```bash
ping silvasonic.local
# Falls nicht: IP direkt nutzen
ssh admin@<IP>
```

### SSH Fehler: "Remote Host Identification Has Changed"

Wenn du von der SD-Karte auf die SSD wechselst, ändert sich der "Fingerabdruck" des Servers. Dein PC blockiert die Verbindung aus Sicherheit.

**Lösung:** Alten Key entfernen:

```bash
ssh-keygen -R silvasonic.local
# bzw.
ssh-keygen -R <IP-ADRESSE>
```

### Ansible findet Pi nicht

```bash
# SSH-Alias prüfen
ssh $SSH_TARGET
# Manuell testen
ansible all -i setup/provision/inventory.yml -m ping
```

### Git clone schlägt fehl

```bash
# Auf dem Pi: Netzwerk prüfen
ping github.com
# Falls kein Internet: WiFi verbinden
sudo nmcli device wifi connect "SSID" password "PSK"
```
