#!/bin/bash
set -euo pipefail

# === KONFIGURATION ===
# Standard: 30 Sekunden Aufnahme für Quick-Check.
# Du kannst es beim Aufruf ändern: ./sound_check.sh 60
DURATION="${1:-30}"
RATE="384000"
BIT_DEPTH="24"
OUT_DIR="/mnt/data/storage/soundlab/raw"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="soundcheck_${TIMESTAMP}.wav"
FILEPATH="${OUT_DIR}/${FILENAME}"
SPECTRO_PATH="${OUT_DIR}/${FILENAME%.wav}_spectrogram.png"

echo "=== SILVASONIC AUDIO LAB ==="

# 1. Hardware Suche
echo "[1/5] Suche UltraMic..."
# Wir suchen nach UltraMic oder Dodotronic
CARD_INFO=$(arecord -l | grep -i -E "UltraMic|Dodotronic")

if [ -z "$CARD_INFO" ]; then
    echo "FEHLER: Kein UltraMic gefunden!"
    echo "Verfügbare Karten:"
    arecord -l
    exit 1
fi

# Extrahiere die Kartennummer (hinter "card")
CARD_ID=$(echo "$CARD_INFO" | awk '{print $2}' | tr -d ':')
echo "-> Gefunden auf Karte ${CARD_ID}: ${CARD_INFO}"

# 2. Ordner erstellen
mkdir -p "$OUT_DIR"

# 3. Aufnahme (sox)
echo "[2/5] Starte Aufnahme (${DURATION}s @ ${RATE}Hz, 24-bit)..."
# -t alsa hw:X,0 = Hardware direkt ansprechen (geringste Latenz)
sox -t alsa "hw:${CARD_ID},0" \
    -c 1 -r "$RATE" -b "$BIT_DEPTH" \
    "$FILEPATH" \
    trim 0 "$DURATION"

echo "-> Gespeichert: $FILEPATH"

# 4. Metadaten Check
echo "[3/5] Prüfe Metadaten (soxi)..."
soxi "$FILEPATH"

# 5. Statistik (Max Amp, Frequenzen)
echo "[4/5] Berechne Statistik..."
# 2>&1 weil sox stat auf stderr schreibt
sox "$FILEPATH" -n stat 2>&1 | grep -E "Maximum amplitude|Rough frequency"

# 6. Spektrogramm
sox "$FILEPATH" -n spectrogram -X 100 -Y 1024 -z 100 -w Hann -o "$SPECTRO_PATH"
echo "-> Bild gespeichert: $SPECTRO_PATH"

echo "=== FERTIG ==="
echo "Du kannst die Dateien jetzt prüfen."
