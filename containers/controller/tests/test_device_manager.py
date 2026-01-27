from unittest.mock import AsyncMock, mock_open, patch

import pytest
from silvasonic_controller.device_manager import AudioDevice, DeviceManager

SAMPLE_ARECORD_OUTPUT = """
card 0: PCH [HDA Intel PCH], device 0: ALC257 Analog [ALC257 Analog]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: Device [USB Audio Device], device 0: USB Audio [USB Audio]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
"""


@pytest.mark.asyncio
async def test_scan_devices(mock_subprocess) -> None:
    ctrl = DeviceManager()

    # Mock asyncio.create_subprocess_exec
    process_mock = mock_subprocess(stdout_bytes=SAMPLE_ARECORD_OUTPUT.encode())

    with patch(
        "asyncio.create_subprocess_exec", new_callable=lambda: AsyncMock(return_value=process_mock)
    ):
        # Mock reading USB ID (which is now in to_thread, so we patch open directly works if to_thread runs in sync context of test or we mock to_thread/open)
        # Note: asyncio.to_thread runs in a thread. Patching 'builtins.open' in the main thread MIGHT not affect the worker thread depending on how patch works (usually it patches the module dict, which is shared).
        # Let's verify.

        with patch("builtins.open", mock_open(read_data="1234:5678")):
            with patch("os.path.exists", return_value=True):
                devices = await ctrl.scan_devices()

    assert len(devices) == 2

    # Check Card 1 (USB)
    usb_dev = next(d for d in devices if d.card_id == "1")
    assert usb_dev.name == "USB Audio Device"
    assert usb_dev.usb_id == "1234:5678"
    assert usb_dev.dev_path == "/dev/snd/pcmC1D0c"


@pytest.mark.asyncio
async def test_scan_devices_error(mock_subprocess) -> None:
    ctrl = DeviceManager()
    with patch("asyncio.create_subprocess_exec", side_effect=Exception("Boom")):
        devices = await ctrl.scan_devices()
        assert devices == []


@pytest.mark.asyncio
async def test_get_usb_id_missing() -> None:
    ctrl = DeviceManager()
    with patch("os.path.exists", return_value=False):
        assert await ctrl._get_usb_id("1") is None


def test_monitoring() -> None:
    # This remains sync
    with patch("pyudev.Context"), patch("pyudev.Monitor.from_netlink") as mock_monitor_cls:
        ctrl = DeviceManager()
        monitor = ctrl.start_monitoring()
        assert monitor == mock_monitor_cls.return_value
        monitor.start.assert_called_once()


def test_device_hash() -> None:
    d1 = AudioDevice(name="A", card_id="1", dev_path="p", usb_id="u")
    d2 = AudioDevice(name="B", card_id="1", dev_path="x", usb_id="y")
    assert hash(d1) == hash(d2)
    assert d1 != d2


@pytest.mark.asyncio
async def test_get_usb_id_exception() -> None:
    ctrl = DeviceManager()
    # Mocking open in thread:
    with patch("builtins.open", side_effect=OSError("Read error")):
        with patch("os.path.exists", return_value=True):
            assert await ctrl._get_usb_id("1") is None
