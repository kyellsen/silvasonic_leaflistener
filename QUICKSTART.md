# 🚀 QUICKSTART

> **Neuer Raspberry Pi → Laufender Leaflistener in 30 Minuten**

---

## Der 2+1 Workflow

```
WORKSTATION                           RASPBERRY PI
───────────────────────────────────────────────────────────────────
1. prepare_stick.sh  ──► USB-Stick ──►  2. flash_ssd.sh
                                              │
3. install.sh  ────────── SSH ───────────────►
                                              │
                                        4. Container starten
```

| Script             | Wo                | Was                  |
| ------------------ | ----------------- | -------------------- |
| `prepare_stick.sh` | Workstation       | Boot-Stick erstellen |
| `flash_ssd.sh`     | Pi (vom Stick)    | NVMe flashen         |
| `install.sh`       | Workstation → SSH | Ansible provisioning |

---

## Kurzversion (für Erfahrene)

```bash
# ═══════════════════════════════════════════════════════════════
# 1. WORKSTATION: Boot-Stick erstellen
# ═══════════════════════════════════════════════════════════════
cd ~/dev/silvasonic_leaflistener
cp setup/config.example.env setup/config/config.env
nano setup/config/config.env                      # Werte anpassen!
# SD-Karte mit Raspi OS Lite flashen (Pi Imager)
sudo ./setup/bootstrap/prepare_stick.sh           # Bootstrap hinzufügen

# ═══════════════════════════════════════════════════════════════
# 2. PI: NVMe flashen (von SD gebootet)
# ═══════════════════════════════════════════════════════════════
ssh pi@silvasonic.local
cd ~/setup_files && sudo ./flash_ssd.sh
sudo poweroff                                     # SD entfernen!

# ═══════════════════════════════════════════════════════════════
# 3. WORKSTATION: Ansible via SSH
# ═══════════════════════════════════════════════════════════════
./setup/install.sh                                # Verbindet zu Pi

# ═══════════════════════════════════════════════════════════════
# 4. PI: Repo klonen & Container starten
# ═══════════════════════════════════════════════════════════════
ssh admin@silvasonic.local
cd /mnt/data/dev
git clone https://github.com/kyellsen/silvasonic_leaflistener.git
cd silvasonic_leaflistener
sudo mkdir -p /mnt/data/storage/leaflistener/raw
sudo podman-compose -f podman-compose.yml up --build -d
sudo podman logs -f silvasonic_ear
```

---

## Detaillierte Anleitung

Siehe [setup/README.md](setup/README.md) für die vollständige Schritt-für-Schritt-Anleitung.

---

## Container & Mikrofone

Siehe [docs/deployment.md](docs/deployment.md) für:

- Mikrofon-Profile
- Troubleshooting
- Container-Konfiguration
