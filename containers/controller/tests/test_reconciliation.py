import time
from unittest.mock import AsyncMock, patch

import pytest
from silvasonic_controller.device_manager import AudioDevice
from silvasonic_controller.main import Controller, SessionInfo


# Mock Dependencies
@pytest.fixture
def mock_deps():
    with (
        patch("silvasonic_controller.main.DeviceManager") as dm,
        patch("silvasonic_controller.main.PodmanOrchestrator") as po,
        patch("silvasonic_controller.main.load_profiles") as lp,
    ):
        dm_instance = dm.return_value
        dm_instance.scan_devices = AsyncMock(return_value=[])

        po_instance = po.return_value
        po_instance.list_active_recorders = AsyncMock(return_value=[])
        po_instance.spawn_recorder = AsyncMock(return_value=True)

        lp.return_value = []
        yield dm, po, lp


@pytest.mark.asyncio
async def test_reconciliation_healthy(mock_deps):
    """Test that healthy containers don't trigger restarts and reset counters."""
    dm, po, lp = mock_deps
    ctrl = Controller(dm.return_value, po.return_value)

    # 1. Setup Session that is supposedly running
    session = SessionInfo(
        container_name="silvasonic_recorder_test",
        rec_id="test_id",
        port=8000,
        profile_slug="test",
        created_at=time.time() - 600,  # Created 10 mins ago
        failure_count=5,  # Was unstable before
    )
    ctrl.active_sessions["card1"] = session

    # 2. Mock Podman reporting it running
    po.return_value.list_active_recorders.return_value = [{"Names": ["silvasonic_recorder_test"]}]

    # 3. Run ONE loop iteration
    # We modify running=False inside the loop or mock asyncio.sleep to break exception?
    # Better: Call health_check_loop once via trickery or just extract logic?
    # Since health_check_loop is a while(self.running), we can set self.running = False after 1st iter?
    # No, it checks `while self.running`. If we set it to false inside, we need a hook.
    # Alternatively, we can run it as a task and cancel it, but verifying state is racey.

    # Let's override asyncio.sleep to stop the loop
    async def stop_loop(*args):
        ctrl.running = False

    with patch("asyncio.sleep", side_effect=stop_loop):
        await ctrl.health_check_loop()

    # 4. Verify
    assert session.failure_count == 0  # Should have reset due to > 300s stability
    po.return_value.spawn_recorder.assert_not_called()


@pytest.mark.asyncio
async def test_reconciliation_crash_restart(mock_deps):
    """Test that missing container triggers restart."""
    dm, po, lp = mock_deps
    ctrl = Controller(dm.return_value, po.return_value)

    session = SessionInfo(
        container_name="silvasonic_recorder_test",
        rec_id="test_id",
        port=8000,
        profile_slug="test",
        failure_count=0,
    )
    ctrl.active_sessions["card1"] = session

    # Podman returns EMPTY list (Analogy: Crash)
    po.return_value.list_active_recorders.return_value = []

    # Need Device Manager to return device for restart
    dm.return_value.scan_devices = AsyncMock(
        return_value=[AudioDevice(name="Mic", card_id="card1", dev_path="/dev/snd/pcmC1D0c")]
    )

    async def stop_loop(*args):
        ctrl.running = False

    with patch("asyncio.sleep", side_effect=stop_loop):
        await ctrl.health_check_loop()

    # Verify Restart
    po.return_value.spawn_recorder.assert_called_once()
    assert session.failure_count == 1
    assert session.next_retry_timestamp > time.time()  # Backoff set


@pytest.mark.asyncio
async def test_reconciliation_backoff_active(mock_deps):
    """Test that backoff prevents immediate restart."""
    dm, po, lp = mock_deps
    ctrl = Controller(dm.return_value, po.return_value)

    session = SessionInfo(
        container_name="silvasonic_recorder_test",
        rec_id="test_id",
        port=8000,
        profile_slug="test",
        failure_count=2,
        next_retry_timestamp=time.time() + 100,  # FUTURE
    )
    ctrl.active_sessions["card1"] = session

    po.return_value.list_active_recorders.return_value = []  # Missing

    async def stop_loop(*args):
        ctrl.running = False

    with patch("asyncio.sleep", side_effect=stop_loop):
        await ctrl.health_check_loop()

    # Verify NO Restart
    po.return_value.spawn_recorder.assert_not_called()
    # Failure count unchanged
    assert session.failure_count == 2
