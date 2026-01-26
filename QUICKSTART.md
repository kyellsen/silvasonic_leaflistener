# 🚀 QUICKSTART

> **Neuer Raspberry Pi → Laufender Silvasonic in wenigen Schritten**

---

## Der "Zero-to-Hero" Ablauf

Dies ist der **vollständige, eigenständige Weg**, um ein komplett leeres System aufzusetzen.

### Voraussetzungen

- **Workstation** (Linux/Mac)
- **Raspberry Pi 5** + NVMe SSD
- **SD-Karte** (leer, für Bootstrap)
- **OS-Image**: Lade `Raspberry Pi OS Lite (64-bit)` herunter.

---

### Schritt 1: Config auf Workstation vorbereiten

Einmalig auf deinem Rechner ausführen, um Passwörter und SSH-Keys festzulegen.

```bash
cd ~/dev/silvasonic

# 1. Config anlegen
mkdir -p setup/config
cp setup/config/bootstrap.example.env setup/config/bootstrap.env

# 2. Config bearbeiten (WICHTIG!)
# Setze USER_PASSWORD_HASH und SSH_PUB_KEY
nano setup/config/bootstrap.env
```

> 💡 **Tipp:** Passwort-Hash generieren: `echo 'dein_passwort' | openssl passwd -6 -stdin`

### Schritt 2: Master-Stick erstellen (Workstation)

Wir erstellen eine SD-Karte, die nur zum einmaligen Flashen der NVMe dient.

1.  **SD-Karte flashen:**
    - Nutze den Raspberry Pi Imager.
    - Wähle OS: Raspberry Pi OS Lite (64-bit).
    - Wähle SD-Karte → Schreiben.
    - (Keine Customization nötig).

2.  **Bootstrap-Dateien hinzufügen:**
    - SD-Karte einmal rausziehen und neu einstecken.
    - Script ausführen:

```bash
sudo ./setup/bootstrap/prepare_stick.sh
```

### Schritt 3: NVMe Flashen (auf dem Pi)

1.  Stecke die SD-Karte in den Pi.
2.  Schalte den Pi ein.
3.  Verbinde dich per SSH user `pi` (Passwort 'raspberry' oder wie im Imager gesetzt):

```bash
ssh pi@silvasonic.local
```

4.  Führe den Flash-Vorgang aus:

```bash
cd ~/setup_files
sudo ./flash_ssd.sh
# Warten bis fertig...
sudo poweroff
```

### Schritt 4: Reboot von NVMe

⚠️ **SD-Karte entfernen!**

1.  Pi einschalten.
2.  Er bootet nun von der schnellen NVMe SSD.

> [!WARNING]
> **SSH Host Key Fehler (REMOTE HOST IDENTIFICATION HAS CHANGED)**
> Da wir das Betriebssystem gewechselt haben (SD → SSD), hat der Pi einen neuen "Fingerabdruck". Dein PC wird warnen: `Host key verification failed`.

**Lösung:** Lösche den alten Key von deinem PC:

```bash
ssh-keygen -R silvasonic.local
# Oder falls du IP nutzt: ssh-keygen -R 192.168.188.129
```

### Schritt 5: Installation & Sync (Workstation)

Zurück auf deinem Rechner. Dieses Script verbindet sich per SSH, synchronisiert dein lokales Repository auf den Pi und startet alles.

```bash
cd ~/dev/silvasonic
./setup/install.sh
```

**Was passiert:**

- Installations-Pakete werden auf dem Pi eingerichtet.
- Dein lokaler Code wird nach `/mnt/data/dev/silvasonic` gesynct (via `rsync`).
- Die Container-Images werden direkt auf dem Pi gebaut (via Podman, Python 3.11).
- Der `silvasonic.service` wird aktiviert und gestartet.

### Schritt 6: Konfiguration (Optional)

Da wir die Config oft schon lokal vorbereiten, ist dieser Schritt meist optional. Falls du Geheimnisse (Nextcloud Passwort) ändern willst:

```bash
ssh admin@silvasonic.local
nano /mnt/data/dev/silvasonic/.env
sudo systemctl restart silvasonic
```

## 🏁 Fertig!

Dein Silvasonic läuft bereits (als System-Service).

**Logs prüfen:**

```bash
ssh admin@silvasonic.local
journalctl -fu silvasonic
```

**Dashboard aufrufen:** Öffne `http://silvasonic.local:8080` in deinem Browser.

### Nützliche Befehle (Auf dem Pi)

Neuladen und bauen:

```bash
sudo podman-compose up -d --build
```

Aufräumen (Speicherplatz freigeben):

```bash
# Löscht alle ungenutzten Images und Container
sudo podman system prune

# Die "Atombombe" (Alles löschen, außer Volumes):
sudo podman system prune -a --volumes
```