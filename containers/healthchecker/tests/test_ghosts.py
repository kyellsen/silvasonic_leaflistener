import json
import os
import time
from unittest.mock import MagicMock, patch

import pytest
from silvasonic_healthchecker.main import (
    RECORDER_GHOST_THRESHOLD,
    check_services_status,
)


@pytest.fixture
def mock_status_dir(tmp_path):
    """Mock the status directory."""
    with patch("silvasonic_healthchecker.main.STATUS_DIR", str(tmp_path)):
        yield tmp_path


def test_ghost_recorder_cleanup(mock_status_dir):
    """Test that stale recorder files are deleted."""

    # 1. Create a "Live" recorder status file (1 minute old)
    live_file = mock_status_dir / "recorder_live.json"
    live_data = {
        "service": "recorder",
        "timestamp": time.time() - 60,
        "status": "Recording",
        "cpu_percent": 10.0,
        "memory_usage_mb": 50.0,
        "pid": 123,
        "meta": {"profile": {"name": "Test Mic"}},
    }
    with open(live_file, "w") as f:
        json.dump(live_data, f)

    # 2. Create a "Ghost" recorder status file (20 minutes old - way past 5 min threshold)
    ghost_file = mock_status_dir / "recorder_ghost.json"
    ghost_data = {
        "service": "recorder",
        "timestamp": time.time() - (RECORDER_GHOST_THRESHOLD + 600),
        "status": "Recording",
        "cpu_percent": 0.0,
        "memory_usage_mb": 0.0,
        "pid": 999,
        "meta": {"profile": {"name": "Ghost Mic"}},
    }
    with open(ghost_file, "w") as f:
        json.dump(ghost_data, f)
    # Explicitly set mtime to the past
    ghost_mtime = time.time() - (RECORDER_GHOST_THRESHOLD + 600)
    os.utime(ghost_file, (ghost_mtime, ghost_mtime))

    # 3. Create a "Stale but not Ghost" recorder status file (4 minutes old - within 5 min threshold)
    # expect this to be reported as DOWN but NOT deleted
    stale_file = mock_status_dir / "recorder_stale.json"
    stale_data = {
        "service": "recorder",
        "timestamp": time.time() - (RECORDER_GHOST_THRESHOLD - 60),
        "status": "Recording",
        "cpu_percent": 0.0,
        "memory_usage_mb": 0.0,
        "pid": 888,
        "meta": {"profile": {"name": "Stale Mic"}},
    }
    with open(stale_file, "w") as f:
        json.dump(stale_data, f)
    # Explicitly set mtime to the past
    stale_mtime = time.time() - (RECORDER_GHOST_THRESHOLD - 60)
    os.utime(stale_file, (stale_mtime, stale_mtime))

    # Mock Mailer
    mock_mailer = MagicMock()

    # Run Check
    check_services_status(mock_mailer, {})

    # Assertions

    # 1. Live file should still exist
    assert live_file.exists(), "Live recorder file should persist"

    # 2. Stale file should still exist (it's not a ghost yet, just down)
    assert stale_file.exists(), "Stale (but not ghost) recorder file should persist"

    # 3. Ghost file should be GONE
    assert not ghost_file.exists(), "Ghost recorder file should have been deleted"

    # Check the result if we could inspect system_status.json (impl detail: it writes to file)
    status_output = mock_status_dir / "system_status.json"
    assert status_output.exists()

    with open(status_output) as f:
        status = json.load(f)

    assert "recorder_live" in status
    assert "recorder_stale" in status
    assert "recorder_ghost" not in status

    assert status["recorder_live"]["status"] == "Running"
    assert status["recorder_stale"]["status"] == "Down"
