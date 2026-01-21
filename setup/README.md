# Silvasonic Setup Guide

> **Clear 2+1 Workflow**: Boot Stick erstellen → SSD flashen → Ansible provisionieren

---

## Übersicht

```
┌─────────────────────────────────────────────────────────────────────────┐
│  WORKSTATION                                                            │
│  ├── 1. prepare_stick.sh  → Boot-USB erstellen                          │
│  └── 3. install.sh        → Ansible via SSH ausführen                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  RASPBERRY PI                                                           │
│  └── 2. flash_ssd.sh      → NVMe flashen (läuft auf dem Pi, von Stick)  │
└─────────────────────────────────────────────────────────────────────────┘
```

| Script             | Läuft auf         | Zweck                                         |
| ------------------ | ----------------- | --------------------------------------------- |
| `prepare_stick.sh` | Workstation       | Boot-Stick mit OS-Image + Bootstrap erstellen |
| `flash_ssd.sh`     | Pi (vom Stick)    | NVMe flashen, SSD-Boot vorbereiten            |
| `install.sh`       | Workstation → SSH | Ansible-Provisioning (WiFi, Pakete, Storage)  |

> [!IMPORTANT]
> **Das Repo kommt IMMER von GitHub!**  
> Der USB-Stick enthält nur Bootstrap-Scripts + OS-Image.

---

## Voraussetzungen

- Raspberry Pi 5 (oder 4)
- NVMe SSD + HAT
- SD-Karte oder USB-Stick (temporär für Bootstrap)
- Workstation (Linux/Mac) mit `ansible` installiert

---

## Phase A: Boot-Stick erstellen (Workstation)

### A.1) Konfiguration vorbereiten

```bash
cd ~/dev/silvasonic_leaflistener
mkdir -p setup/config
cp setup/config.example.env setup/config/config.env
nano setup/config/config.env
```

**Wichtige Werte:**

```bash
# Passwort-Hash generieren
echo 'dein_passwort' | openssl passwd -6 -stdin
```

### A.2) OS-Image auf SD schreiben

**Option 1: Raspberry Pi Imager**

1. Raspberry Pi Imager öffnen
2. OS: `Raspberry Pi OS Lite (64-bit)`
3. SD-Karte auswählen → **Schreiben**

**Option 2: Beliebiger Imager**

- Normales Raspi OS Lite auf SD schreiben

### A.3) Bootstrap-Dateien hinzufügen

```bash
# SD-Karte neu einstecken
sudo ./setup/bootstrap/prepare_stick.sh
```

Das Script:

- Erweitert die Partition auf volle Größe
- Kopiert `flash_ssd.sh` + OS-Image + Config auf den Stick
- Aktiviert SSH

**SD-Karte auswerfen → fertig!**

---

## Phase B: NVMe flashen (auf dem Pi)

### B.1) Von SD booten

```bash
# Pi einschalten mit SD-Karte
ssh pi@silvasonic.local
# Passwort: aus deiner config.env
```

### B.2) SSD flashen

```bash
cd ~/setup_files
sudo ./flash_ssd.sh
sudo poweroff
```

### B.3) SD-Karte entfernen → Von NVMe booten

Pi startet jetzt von der SSD.

---

## Phase C: Ansible Provisioning (Workstation → SSH)

### C.1) Verbindung testen

```bash
ssh admin@silvasonic.local
# Passwort: aus deiner config.env
exit
```

### C.2) Install-Script ausführen

> [!IMPORTANT]
> Das Script läuft auf deiner **Workstation** und verbindet sich via SSH!

```bash
cd ~/dev/silvasonic_leaflistener
./setup/install.sh
```

**Was passiert:**

1. Verbindet sich via SSH zum Pi
2. Führt Ansible-Playbooks aus:
   - WiFi konfigurieren
   - Pakete installieren (Podman, Git, etc.)
   - Storage-Struktur auf `/mnt/data` anlegen
   - Podman für SSD optimieren

### C.3) Pi neustarten (optional)

```bash
ssh admin@silvasonic.local 'sudo reboot'
```

---

## Phase D: Repo klonen & Container starten

### D.1) Repo von GitHub

```bash
ssh admin@silvasonic.local
cd /mnt/data/dev
git clone https://github.com/kyellsen/silvasonic_leaflistener.git
cd silvasonic_leaflistener
```

### D.2) Container starten

```bash
sudo mkdir -p /mnt/data/storage/leaflistener/raw
sudo podman-compose -f podman-compose.yml up --build -d
sudo podman logs -f silvasonic_ear
```

Mehr Details: [docs/deployment.md](../docs/deployment.md)

---

## Updates

```bash
cd /mnt/data/dev/silvasonic_leaflistener
git pull
sudo podman-compose -f podman-compose.yml down
sudo podman-compose -f podman-compose.yml up --build -d
```

---

## Troubleshooting

### SSH funktioniert nicht

```bash
# Hostname auflösen
ping silvasonic.local

# Falls nicht gefunden, IP direkt nutzen
ssh admin@<IP_ADRESSE>
```

### Ansible schlägt fehl

```bash
# Manuell mit Verbose ausführen
ansible-playbook -i setup/provision/inventory.yml \
    setup/provision/main.yml -vvv
```

### Git clone fehlgeschlagen

```bash
# Netzwerk prüfen
ping github.com

# WiFi verbinden (falls noch nicht)
sudo nmcli device wifi connect "SSID" password "PSK"
```
