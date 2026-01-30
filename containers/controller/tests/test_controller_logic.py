import json
from unittest.mock import AsyncMock, patch

import pytest
from silvasonic_controller.device_manager import AudioDevice
from silvasonic_controller.main import Controller
from silvasonic_controller.profiles_loader import MicrophoneProfile


@pytest.fixture
def mock_deps():
    with (
        patch("silvasonic_controller.main.DeviceManager") as dm,
        patch("silvasonic_controller.main.PodmanOrchestrator") as po,
        patch("silvasonic_controller.main.load_profiles") as lp,
        patch("silvasonic_controller.main.psutil") as mock_psutil,
    ):
        dm_instance = dm.return_value
        dm_instance.scan_devices = AsyncMock(return_value=[])

        po_instance = po.return_value
        po_instance.spawn_recorder = AsyncMock(return_value=True)
        po_instance.list_active_recorders = AsyncMock(return_value=[])

        lp.return_value = [
            MicrophoneProfile(name="Test Profile", slug="test_profile", device_patterns=["Test"])
        ]

        # Configure psutil mock
        mock_psutil.cpu_percent.return_value = 5.0
        mock_psutil.Process.return_value.memory_info.return_value.rss = 50 * 1024 * 1024

        yield dm, po, lp


@pytest.mark.asyncio
async def test_reconcile_unconfigured_device(mock_deps) -> None:
    """Test that a device with no profile is added to unconfigured_devices."""
    dm, po, lp = mock_deps
    ctrl = Controller(dm.return_value, po.return_value)

    # Setup: Device that does NOT match "Test Profile"
    unknown_device = AudioDevice(
        name="Unknown Mic", card_id="5", dev_path="/dev/snd/pcmC5D0c", usb_id="1234:5678"
    )
    dm.return_value.scan_devices.return_value = [unknown_device]

    # Patch write methods to avoid side effects
    with (
        patch.object(ctrl, "write_status", new_callable=AsyncMock),
    ):
        await ctrl.reconcile()

    # Verify logic
    assert len(ctrl.unconfigured_devices) == 1
    assert ctrl.unconfigured_devices[0] == unknown_device

    # Verify NO spawn
    po.return_value.spawn_recorder.assert_not_called()


@pytest.mark.asyncio
async def test_reconcile_clears_unconfigured(mock_deps) -> None:
    """Test that unconfigured list is reset on each reconcile."""
    dm, po, lp = mock_deps
    ctrl = Controller(dm.return_value, po.return_value)

    # Pre-populate with stale data
    ctrl.unconfigured_devices.append(AudioDevice("Stale", "99", "path"))

    # Setup: No devices found
    dm.return_value.scan_devices.return_value = []

    with (
        patch.object(ctrl, "write_status", new_callable=AsyncMock),
    ):
        await ctrl.reconcile()

    assert len(ctrl.unconfigured_devices) == 0


@pytest.mark.asyncio
async def test_write_status_includes_unconfigured(mock_deps) -> None:
    """Test that controller.json includes the unconfigured devices list."""
    dm, po, lp = mock_deps
    ctrl = Controller(dm.return_value, po.return_value)

    # Populate state
    device = AudioDevice(name="Mystery Mic", card_id="7", dev_path="p", usb_id="USER:PROBLEM")
    ctrl.unconfigured_devices = [device]

    # Mock Redis instead of open
    ctrl.redis = AsyncMock()

    await ctrl.write_status()

    # Verify Redis set call
    ctrl.redis.set.assert_called_once()
    args, kwargs = ctrl.redis.set.call_args
    assert args[0] == "status:controller"
    data = json.loads(args[1])

    assert "unconfigured_devices" in data
    assert len(data["unconfigured_devices"]) == 1
    assert data["unconfigured_devices"][0]["name"] == "Mystery Mic"
    assert data["unconfigured_devices"][0]["usb_id"] == "USER:PROBLEM"
