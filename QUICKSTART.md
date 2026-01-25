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

> 💡 **Passwort-Hash generieren:**
> `echo 'dein_passwort' | openssl passwd -6 -stdin`

---

### Schritt 2: Master-Stick erstellen (Workstation)

Wir erstellen eine SD-Karte, die nur zum einmaligen Flashen der NVMe dient.

1. **SD-Karte flashen**:
   - Nutze den **Raspberry Pi Imager**.
   - Wähle OS: `Raspberry Pi OS Lite (64-bit)`.
   - Wähle SD-Karte → **Schreiben**.
   - (Keine Customization nötig).

2. **Bootstrap-Dateien hinzufügen**:
   - SD-Karte einmal rausziehen und neu einstecken.
   - Script ausführen:

```bash
sudo ./setup/bootstrap/prepare_stick.sh
```

---

### Schritt 3: NVMe Flashen (auf dem Pi)

1. Stecke die SD-Karte in den Pi.
2. Schalte den Pi ein.
3. Verbinde dich per SSH (Passwort 'raspberry' oder wie im Imager gesetzt):
   ```bash
   ssh pi@silvasonic.local
   ```
4. Führe den Flash-Vorgang aus:
   ```bash
   cd ~/setup_files
   sudo ./flash_ssd.sh
   # Warten bis fertig...
   sudo poweroff
   ```

---

### Schritt 4: Reboot von NVMe

1. ⚠️ **SD-Karte entfernen!**
2. Pi einschalten.
3. Er bootet nun von der schnellen NVMe SSD.

> [!WARNING]
> **SSH Host Key Fehler (REMOTE HOST IDENTIFICATION HAS CHANGED)**
> Da wir das Betriebssystem gewechselt haben (SD → SSD), hat der Pi einen neuen "Fingerabdruck". Dein PC wird warnen:
> `Host key verification failed.`
>
> **Lösung:** Lösche den alten Key von deinem PC:
>
> ```bash
> ssh-keygen -R silvasonic.local
> # Oder falls du IP nutzt: ssh-keygen -R 192.168.188.129
> ```

---

### Schritt 5: Installation & Repo (Workstation)

Zurück auf deinem Rechner. Dieses Script verbindet sich per SSH, **klont das Repo** und richtet alles ein.

```bash
cd ~/dev/silvasonic
./setup/install.sh
```

_Das Script installiert Podman, richtet Verzeichnisse ein und klont den Code nach `/mnt/data/dev/silvasonic`._

---

---

### Schritt 6: Carrier (Nextcloud) Konfiguration

Damit deine Aufnahmen automatisch hochgeladen werden, musst du die `.env` Datei konfigurieren.

1. **Konfigurations-Datei erstellen**:

   ```bash
   # Auf dem Pi:
   cd /mnt/data/dev/silvasonic
   cp config.example.env .env
   ```

2. **Zugangsdaten eintragen**:
   Öffne die Datei und trage deine Nextcloud-URL, Benutzer und App-Passwort ein:

   ```bash
   nano .env
   ```

   ```ini
   CARRIER_NEXTCLOUD_URL=https://deine-nextcloud.de/remote.php/webdav/
   CARRIER_NEXTCLOUD_USER=dein_nutzer
   CARRIER_NEXTCLOUD_PASSWORD=dein_app_passwort
   CARRIER_TARGET_DIR=silvasonic
   ```

---

### 🏁 Fertig! Container starten

Dein Silvasonic ist bereit.

```bash
# 1. Auf den Pi verbinden
ssh admin@silvasonic.local

# 2. In das geklonte Repo wechseln
cd /mnt/data/dev/silvasonic

# 3. Starten
sudo podman-compose -f podman-compose.yml up --build -d

# 4. Logs prüfen
sudo podman logs -f silvasonic_ear
```
