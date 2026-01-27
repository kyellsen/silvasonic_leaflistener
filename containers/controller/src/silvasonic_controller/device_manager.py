import asyncio
import logging
import os
import re
from dataclasses import dataclass

import pyudev

logger = logging.getLogger("DeviceManager")


@dataclass
class AudioDevice:
    name: str  # e.g. "Usb Audio Device"
    card_id: str  # e.g. "1"
    dev_path: str  # e.g. "/dev/snd/pcmC1D0c" (inferred)
    usb_id: str | None = None  # e.g. "1b3f:2008" (Vendor:Product)

    def __hash__(self) -> int:
        return hash(self.card_id)


class DeviceManager:
    def __init__(self) -> None:
        self.context = pyudev.Context()
        self.monitor = pyudev.Monitor.from_netlink(self.context)
        self.monitor.filter_by(subsystem="sound")

    async def scan_devices(self) -> list[AudioDevice]:
        """Scan active ALSA capture devices asynchronously."""
        devices = []
        try:
            # Async subprocess call
            process = await asyncio.create_subprocess_exec(
                "arecord",
                "-l",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            output = stdout.decode() if stdout else ""

            # Example Output:
            # card 1: Device [USB Audio Device], device 0: USB Audio [USB Audio]

            for line in output.split("\n"):
                match = re.search(r"card (\d+): (.*?) \[(.*?)\], device (\d+):", line)
                if match:
                    card_id = match.group(1)
                    # card_name = match.group(2) # "Device" often generic
                    card_desc = match.group(3)  # "USB Audio Device" - More useful
                    device_id = match.group(4)

                    usb_id = await self._get_usb_id(card_id)
                    logger.debug(f"Card {card_id} ({card_desc}) USB ID: {usb_id}")

                    devices.append(
                        AudioDevice(
                            name=card_desc,
                            card_id=card_id,
                            dev_path=f"/dev/snd/pcmC{card_id}D{device_id}c",
                            usb_id=usb_id,
                        )
                    )
        except Exception as e:
            logger.error(f"Scan failed: {e}")

        return devices

    async def _get_usb_id(self, card_id: str) -> str | None:
        """Attempt to find Vendor:Product ID for a card asynchronously."""
        # /proc/asound/cardX/usbid often exists for USB devices
        path = f"/proc/asound/card{card_id}/usbid"

        def _read_file() -> str | None:
            try:
                if os.path.exists(path):
                    with open(path) as f:
                        return f.read().strip()
            except OSError:
                pass
            return None

        # Run file I/O in thread pool to catch all edge cases of blocking
        return await asyncio.to_thread(_read_file)

    def start_monitoring(self) -> pyudev.Monitor:
        """Return the monitor to be polled."""
        # This remains synchronous as it just sets up the netlink socket
        self.monitor.start()
        return self.monitor
