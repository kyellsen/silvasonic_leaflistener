from unittest.mock import mock_open, patch

from silvasonic_controller.device_manager import AudioDevice, DeviceManager

SAMPLE_ARECORD_OUTPUT = """
card 0: PCH [HDA Intel PCH], device 0: ALC257 Analog [ALC257 Analog]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
card 1: Device [USB Audio Device], device 0: USB Audio [USB Audio]
  Subdevices: 1/1
  Subdevice #0: subdevice #0
"""


def test_scan_devices() -> None:
    ctrl = DeviceManager()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = SAMPLE_ARECORD_OUTPUT
        mock_run.return_value.returncode = 0

        # Mock reading USB ID
        with patch("builtins.open", mock_open(read_data="1234:5678")):
            with patch("os.path.exists", return_value=True):
                devices = ctrl.scan_devices()

        assert len(devices) == 2

        # Check Card 1 (USB)
        usb_dev = next(d for d in devices if d.card_id == "1")
        assert usb_dev.name == "USB Audio Device"
        assert usb_dev.usb_id == "1234:5678"
        assert usb_dev.dev_path == "/dev/snd/pcmC1D0c"


def test_scan_devices_error() -> None:
    ctrl = DeviceManager()
    with patch("subprocess.run", side_effect=Exception("Boom")):
        devices = ctrl.scan_devices()
        assert devices == []


def test_get_usb_id_missing() -> None:
    ctrl = DeviceManager()
    with patch("os.path.exists", return_value=False):
        assert ctrl._get_usb_id("1") is None


def test_monitoring() -> None:
    with patch("pyudev.Context"), patch("pyudev.Monitor.from_netlink") as mock_monitor_cls:
        ctrl = DeviceManager()
        monitor = ctrl.start_monitoring()
        assert monitor == mock_monitor_cls.return_value
        monitor.start.assert_called_once()


def test_device_hash() -> None:
    d1 = AudioDevice(name="A", card_id="1", dev_path="p", usb_id="u")
    d2 = AudioDevice(name="B", card_id="1", dev_path="x", usb_id="y")
    assert hash(d1) == hash(d2)
    # They are not equal due to different names, but hash is same based on card_id
    assert d1 != d2


def test_get_usb_id_exception() -> None:
    ctrl = DeviceManager()
    with patch("builtins.open", side_effect=OSError("Read error")):
        with patch("os.path.exists", return_value=True):
            assert ctrl._get_usb_id("1") is None
