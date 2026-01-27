
import logging
import subprocess
import re
import pyudev
import time
import os
import glob
import shlex
from dataclasses import dataclass

logger = logging.getLogger("DeviceManager")

@dataclass
class AudioDevice:
    name: str # e.g. "Usb Audio Device"
    card_id: str # e.g. "1"
    dev_path: str # e.g. "/dev/snd/pcmC1D0c" (inferred)
    usb_id: str | None = None # e.g. "1b3f:2008" (Vendor:Product)

    def __hash__(self) -> int:
         return hash(self.card_id)

class DeviceManager:
    def __init__(self):
        self.context = pyudev.Context()
        self.monitor = pyudev.Monitor.from_netlink(self.context)
        self.monitor.filter_by(subsystem='sound')

    def scan_devices(self) -> list[AudioDevice]:
        """Scan active ALSA capture devices."""
        devices = []
        try:
            # Using arecord -l is reliable for finding CARD IDs
            cmd = ["arecord", "-l"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            output = result.stdout
            
            # Example Output:
            # card 1: Device [USB Audio Device], device 0: USB Audio [USB Audio]
            
            for line in output.split("\n"):
                match = re.search(r"card (\d+): (.*?) \[(.*?)\], device (\d+):", line)
                if match:
                    card_id = match.group(1)
                    # card_name = match.group(2) # "Device" often generic
                    card_desc = match.group(3) # "USB Audio Device" - More useful
                    device_id = match.group(4)
                    
                    usb_id = self._get_usb_id(card_id)
                    logger.debug(f"Card {card_id} ({card_desc}) USB ID: {usb_id}")

                    devices.append(AudioDevice(
                        name=card_desc,
                        card_id=card_id,
                        dev_path=f"/dev/snd/pcmC{card_id}D{device_id}c",
                        usb_id=usb_id
                    ))
        except Exception as e:
            logger.error(f"Scan failed: {e}")
            
        return devices

    def _get_usb_id(self, card_id: str) -> str | None:
        """Attempt to find Vendor:Product ID for a card."""
        # /proc/asound/cardX/usbid often exists for USB devices
        try:
            path = f"/proc/asound/card{card_id}/usbid"
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return f.read().strip()
        except:
            pass
        return None

    def start_monitoring(self) -> pyudev.Monitor:
        """Return the monitor to be polled."""
        self.monitor.start()
        return self.monitor
