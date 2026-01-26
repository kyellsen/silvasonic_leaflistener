#!/bin/bash
echo "=== 1. STORAGE CHECK ==="
lsblk | grep nvme
df -h /mnt/data

echo -e "\n=== 2. SSD SPEED TEST (Gen 3?) ==="
dd if=/dev/zero of=/mnt/data/speedtest bs=1G count=1 oflag=direct
rm /mnt/data/speedtest

echo -e "\n=== 3. AUDIO / MIC CHECK ==="
# Zeigt dein UltraMic und die USB-ID
arecord -l | grep card
lsusb | grep -i "DODOTRONIC" || echo "Kein UltraMic gefunden!"

echo -e "\n=== 4. THERMAL STRESS TEST (10s) ==="
stress -c 4 -t 10 &
for i in {1..10}; do
    TEMP=$(vcgencmd measure_temp)
    FAN=$(cat /sys/class/thermal/cooling_device0/cur_state 2>/dev/null || echo "0")
    echo "Tick $i: $TEMP | Fan-Level: $FAN"
    sleep 1
done

echo -e "\n=== 5. PODMAN CHECK ==="
podman info | grep -E "store|host"
