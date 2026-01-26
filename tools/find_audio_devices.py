#!/usr/bin/env python3
"""
Audio Device Discovery Tool
---------------------------
Lists available ALSA devices and suggests configuration strings for Silvasonic.
Run this script to find the correct 'hw:X,Y' string for your Røde NT or other USB microphones.
"""

import re
import subprocess
import sys


def get_alsa_devices():
    """Get list of ALSA capture devices."""
    print("Scanning ALSA Capture Devices...\n")

    try:
        # Run arecord -l to list capture devices
        result = subprocess.run(["arecord", "-l"], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: arecord returned {result.returncode}")
            print("Make sure 'alsa-utils' is installed.")
            return []

        output = result.stdout
    except FileNotFoundError:
        print("Error: 'arecord' command not found. Please install alsa-utils.")
        return []

    devices = []

    # Parse output like:
    # card 1: SC2 [Røde AI-1], device 0: USB Audio [USB Audio]
    #   Subdevices: 1/1
    #   Subdevice #0: subdevice #0



    lines = output.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Match card line
        match = re.search(r"card (\d+): (.*?) \[(.*?)\], device (\d+): (.*?) \[(.*?)\]", line)
        if match:
            card_id = match.group(1)
            _ = match.group(2)
            card_desc = match.group(3)
            dev_id = match.group(4)
            _ = match.group(5)
            dev_desc = match.group(6)

            hw_address = f"hw:{card_id},{dev_id}"
            plughw_address = f"plughw:{card_id},{dev_id}"

            devices.append(
                {
                    "hw": hw_address,
                    "plughw": plughw_address,
                    "name": f"{card_desc} ({dev_desc})",
                    "full_desc": line,
                }
            )

    return devices


def suggest_config(devices):
    print(f"{'Address':<15} | {'Description'}")
    print("-" * 60)

    rode_found = False

    for dev in devices:
        print(f"{dev['hw']:<15} | {dev['name']}")

        if "rode" in dev["name"].lower() or "nt" in dev["name"].lower():
            rode_found = True
            print(f"   >>> LIKELY RØDE DEVICE! Use hw address: {dev['hw']}")

    print("-" * 60)
    print("\nConfiguration Help:")
    print("1. If using Docker, ensure the device is passed through (--device /dev/snd).")
    print("2. 'hw:X,Y' gives direct hardware access (preferred for low latency).")
    print("3. 'plughw:X,Y' adds software resampling (safer compatibility).")

    if not rode_found:
        print("\n⚠️  No Røde device explicitly detected by name.")


if __name__ == "__main__":
    devices = get_alsa_devices()
    if not devices:
        print("No capture devices found via ALSA.")
        sys.exit(1)

    suggest_config(devices)
