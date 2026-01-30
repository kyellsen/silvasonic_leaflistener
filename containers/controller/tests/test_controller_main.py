import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from silvasonic_controller.device_manager import AudioDevice
from silvasonic_controller.main import Controller, SessionInfo
from silvasonic_controller.profiles_loader import MicrophoneProfile


@pytest.fixture
def mock_deps():
    with (
        patch("silvasonic_controller.main.DeviceManager") as dm,
        patch("silvasonic_controller.main.PodmanOrchestrator") as po,
        patch("silvasonic_controller.main.load_profiles") as lp,
        patch("silvasonic_controller.main.DatabaseClient") as pm,
    ):
        # Setup mock behavior for ASYNC methods
        dm_instance = dm.return_value
        dm_instance.scan_devices = AsyncMock(return_value=[])
        dm_instance.start_monitoring = MagicMock()  # Sync

        po_instance = po.return_value
        po_instance.spawn_recorder = AsyncMock(return_value=True)
        po_instance.stop_recorder = AsyncMock()
        po_instance.list_active_recorders = AsyncMock(return_value=[])

        # PersistenceManager mocks
        pm_instance = pm.return_value
        pm_instance.start = AsyncMock()
        pm_instance.log_event = AsyncMock()
        pm_instance.sync_loop = AsyncMock()
        pm_instance.stop = AsyncMock()

        lp.return_value = [MicrophoneProfile(name="Test", slug="test", device_patterns=["Test"])]

        yield dm, po, lp


def test_setup_logging() -> None:
    from silvasonic_controller.main import setup_logging

    with (
        patch("os.makedirs"),
        patch("logging.basicConfig"),
        patch("logging.handlers.TimedRotatingFileHandler"),
    ):
        setup_logging()


def test_controller_init(mock_deps) -> None:
    dm, po, lp = mock_deps
    ctrl = Controller(dm.return_value, po.return_value)
    assert ctrl.profiles
    assert ctrl.running


@pytest.mark.asyncio
async def test_reconcile_add_new(mock_deps) -> None:
    """Test that a new device spawns a recorder."""
    dm, po, lp = mock_deps
    ctrl = Controller(dm.return_value, po.return_value)

    # Setup Device Manager to return one device
    device = AudioDevice(name="Test Device", card_id="1", dev_path="/dev/snd/pcmC1D0c")
    dm.return_value.scan_devices.return_value = [device]

    await ctrl.reconcile()

    # Expect spawn call
    po.return_value.spawn_recorder.assert_called_once()
    args = po.return_value.spawn_recorder.call_args[1]
    assert args["card_id"] == "1"
    assert args["profile_slug"] == "test"

    # Check session stored
    assert "1" in ctrl.active_sessions


@pytest.mark.asyncio
async def test_reconcile_ignore_existing(mock_deps) -> None:
    """Test that existing sessions are not respawned."""
    dm, po, lp = mock_deps
    ctrl = Controller(dm.return_value, po.return_value)

    # Initial State: Session exists
    ctrl.active_sessions["1"] = SessionInfo("cont", "id", 8003, "slug")

    # Scan returns same device
    device = AudioDevice(name="Test Device", card_id="1", dev_path="...")
    dm.return_value.scan_devices.return_value = [device]

    await ctrl.reconcile()

    po.return_value.spawn_recorder.assert_not_called()


@pytest.mark.asyncio
async def test_reconcile_remove_stale(mock_deps) -> None:
    """Test that removed devices stop the recorder."""
    dm, po, lp = mock_deps
    ctrl = Controller(dm.return_value, po.return_value)

    # Initial sessions
    ctrl.active_sessions["1"] = SessionInfo("cont_1", "id", 8003, "slug")
    ctrl.active_sessions["2"] = SessionInfo("cont_2", "id", 8003, "slug")

    # Scan returns only device 2
    device2 = AudioDevice(name="Test", card_id="2", dev_path="...")
    dm.return_value.scan_devices.return_value = [device2]

    await ctrl.reconcile()

    # Expect stop for device 1
    po.return_value.stop_recorder.assert_called_once_with("cont_1")
    assert "1" not in ctrl.active_sessions
    assert "2" in ctrl.active_sessions


@pytest.mark.asyncio
async def test_reconcile_no_profile_ignore(mock_deps) -> None:
    dm, po, lp = mock_deps

    # Reload with empty profiles
    lp.return_value = []
    ctrl = Controller(dm.return_value, po.return_value)

    # Device that doesn't match any profile
    device = AudioDevice(name="Unknown", card_id="99", dev_path="...")
    dm.return_value.scan_devices.return_value = [device]

    await ctrl.reconcile()
    po.return_value.spawn_recorder.assert_not_called()


@pytest.mark.asyncio
async def test_port_fallback(mock_deps) -> None:
    dm, po, lp = mock_deps
    ctrl = Controller(dm.return_value, po.return_value)

    device = AudioDevice(name="Test", card_id="not_int", dev_path="...")
    dm.return_value.scan_devices.return_value = [device]

    # Force match (simulate successful spawn)
    # Reload orchestrator mock for this specific instance if needed or just use po.return_value
    ctrl.orchestrator.spawn_recorder.return_value = True

    await ctrl.reconcile()

    args = ctrl.orchestrator.spawn_recorder.call_args[1]
    assert "port" not in args

    session = ctrl.active_sessions["not_int"]
    assert session.port > 12000  # Should be calculated via hash


def test_stop_signal(mock_deps) -> None:
    dm, po, lp = mock_deps
    ctrl = Controller(dm.return_value, po.return_value)
    ctrl.stop()
    assert ctrl.running is False


@pytest.mark.asyncio
async def test_run_loop_monitor_event(mock_deps) -> None:
    """Test that the monitor loop catches events and calls reconcile."""
    dm, po, lp = mock_deps
    ctrl = Controller(dm.return_value, po.return_value)

    monitor = MagicMock()
    dm.return_value.start_monitoring.return_value = monitor

    # Mock the monitor returning an event then None
    event = MagicMock()
    event.action = "add"
    event.device_node = "/dev/snd/test"

    # We mock asyncio.to_thread to catch the blocking poll call
    # First call returns event, subsequent call raises CancelledError to stop loop helper?
    # Or we can just stop the controller after short sleep.

    original_to_thread = asyncio.to_thread

    async def mock_poll_thread(func, *args, **kwargs):
        if func == monitor.poll:
            if not getattr(mock_poll_thread, "called", False):
                mock_poll_thread.called = True
                return event
            else:
                # Wait forever second time
                await asyncio.sleep(10)
        return await original_to_thread(func, *args, **kwargs)

    with patch("asyncio.to_thread", side_effect=mock_poll_thread):
        with patch.object(ctrl, "reconcile", new_callable=AsyncMock) as mock_rec:
            # Run controller for a short time
            task = asyncio.create_task(ctrl.run())
            await asyncio.sleep(0.1)
            ctrl.stop()  # Signals stop
            await task

            # Reconcile called initially + once for event
            assert mock_rec.call_count >= 2


@pytest.mark.asyncio
async def test_adopt_orphans(mock_deps) -> None:
    dm, po, lp = mock_deps
    ctrl = Controller(dm.return_value, po.return_value)

    # Mock active recorders
    po.return_value.list_active_recorders.return_value = [
        {
            "Names": ["silvasonic_recorder_old"],
            "Labels": {
                "silvasonic.profile": "test",
                "silvasonic.port": "12001",
                "silvasonic.rec_id": "test_1",
                "card_id": "1",
            },
        },
        {
            "Names": ["random_container"],
            "Labels": {},  # Should be ignored
        },
    ]

    await ctrl.adopt_orphans()

    assert "1" in ctrl.active_sessions
    assert ctrl.active_sessions["1"].container_name == "silvasonic_recorder_old"


@pytest.mark.asyncio
async def test_write_status(mock_deps) -> None:
    dm, po, lp = mock_deps
    ctrl = Controller(dm.return_value, po.return_value)

    # Mock Redis
    ctrl.redis = MagicMock()

    # Needs to be serializable by simplejson/json
    # psutil is mocked in mock_deps but let's ensure return values are simple types

    # Patch json.dumps to avoid serializing MagicMock objects
    with patch("json.dumps", return_value='{"mock": "json"}'):
        await ctrl.write_status()

    ctrl.redis.set.assert_called_once()
    args, kwargs = ctrl.redis.set.call_args
    assert args[0] == "status:controller"


@pytest.mark.asyncio
async def test_reconcile_spawn_failure(mock_deps) -> None:
    dm, po, lp = mock_deps
    ctrl = Controller(dm.return_value, po.return_value)

    device = AudioDevice(name="Test", card_id="1", dev_path="...")
    dm.return_value.scan_devices.return_value = [device]

    po.return_value.spawn_recorder.return_value = False

    await ctrl.reconcile()

    po.return_value.spawn_recorder.assert_called_once()
    assert "1" not in ctrl.active_sessions


@pytest.mark.asyncio
async def test_monitor_hardware_exception(mock_deps) -> None:
    dm, po, lp = mock_deps
    ctrl = Controller(dm.return_value, po.return_value)

    monitor = MagicMock()
    dm.return_value.start_monitoring.return_value = monitor
    monitor.poll.side_effect = Exception("Error")

    # To break the loop after exception
    async def side_effect_sleep(dur):
        ctrl.running = False

    with patch("asyncio.sleep", side_effect=side_effect_sleep):
        await ctrl.monitor_hardware()

    # Ensure it didn't crash
    assert ctrl.running is False
