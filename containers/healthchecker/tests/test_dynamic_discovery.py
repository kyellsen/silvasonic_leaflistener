import json
import time
from unittest.mock import MagicMock, patch

import pytest
from silvasonic_healthchecker.main import check_services_status


@pytest.fixture
def mock_status_dir(tmp_path):
    """Mock the status directory."""
    with patch("silvasonic_healthchecker.main.STATUS_DIR", str(tmp_path)):
        yield tmp_path


def test_dynamic_service_discovery(mock_status_dir):
    """Test that services are discovered dynamically with _instance suffixes."""

    # 1. Create traditional file for BirdNET
    birdnet_file = mock_status_dir / "birdnet.json"
    with open(birdnet_file, "w") as f:
        json.dump({"service": "birdnet", "timestamp": time.time(), "status": "Running"}, f)

    # 2. Create instance file for Uploader
    uploader_file = mock_status_dir / "uploader_myhost.json"
    with open(uploader_file, "w") as f:
        json.dump(
            {
                "service": "uploader",
                "timestamp": time.time(),
                "status": "Running",
                "last_upload": time.time(),
            },
            f,
        )

    # 3. Create MULTIPLE instances for Livesound (if supported by logic, though config might assume singleton if not rigorous)
    # Actually logic supports multiple.
    ls1 = mock_status_dir / "livesound_front.json"
    with open(ls1, "w") as f:
        json.dump({"service": "livesound", "timestamp": time.time(), "status": "Running"}, f)

    ls2 = mock_status_dir / "livesound_back.json"
    with open(ls2, "w") as f:
        json.dump({"service": "livesound", "timestamp": time.time(), "status": "Running"}, f)

    # Mock Mailer
    mock_mailer = MagicMock()

    # Run Check
    check_services_status(mock_mailer, {})

    # Verify Output
    status_output = mock_status_dir / "system_status.json"
    assert status_output.exists()

    with open(status_output) as f:
        status = json.load(f)

    # Check BirdNET (Legacy name)
    assert "birdnet" in status
    assert status["birdnet"]["status"] == "Running"

    # Check Uploader (New name)
    assert "uploader_myhost" in status
    assert status["uploader_myhost"]["status"] == "Running"

    # Check Livesound (Multiple)
    assert "livesound_front" in status
    assert "livesound_back" in status

    # Check Missing Service (e.g. Dashboard if we didn't create file)
    # Dashboard is in SERVICES_CONFIG. We created no file.
    # Logic: if processed_count == 0, add default Down entry.
    assert "dashboard" in status
    assert status["dashboard"]["status"] == "Down"
    assert status["dashboard"]["message"] == "No instance found"


def test_garbage_file_ignore(mock_status_dir):
    """Test that non-matching files or bad json are ignored."""
    # Bad JSON
    bad_file = mock_status_dir / "birdnet_bad.json"
    with open(bad_file, "w") as f:
        f.write("{invalid_json")

    # Wrong Prefix (should be ignored by glob?)
    # glob pattern is "{service}*.json"
    # "birdnet_stats.json" matches "birdnet*.json"
    # But schema validation should fail if it doesn't match ServiceStatus
    stats_file = mock_status_dir / "birdnet_stats.json"
    with open(stats_file, "w") as f:
        # Valid JSON but missing 'timestamp' or fields
        json.dump({"some": "stats", "count": 10}, f)

    mock_mailer = MagicMock()
    check_services_status(mock_mailer, {})

    status_output = mock_status_dir / "system_status.json"
    with open(status_output) as f:
        status = json.load(f)

    # birdnet should be DOWN (No instance found) because valid files were 0
    # (assuming we ignore the bad ones)
    assert status["birdnet"]["status"] == "Down"
    assert "birdnet_bad" not in status
    assert "birdnet_stats" not in status
