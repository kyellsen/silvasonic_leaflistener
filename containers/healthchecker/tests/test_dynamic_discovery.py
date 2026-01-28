import json
import time
from unittest.mock import MagicMock, patch

import pytest
from silvasonic_healthchecker.main import check_services_status


@pytest.fixture
def mock_redis():
    """Mock Redis."""
    with patch("silvasonic_healthchecker.main.redis.Redis") as mock:
        yield mock.return_value


def test_dynamic_service_discovery(mock_redis):
    """Test that services are discovered dynamically via Redis keys."""

    # Setup Mocks
    mock_redis.keys.return_value = [
        b"status:birdnet",
        b"status:uploader:myhost",
        b"status:livesound:front",
        b"status:livesound:back",
    ]

    # Setup key content
    # We use side_effect to return different content based on key
    def get_side_effect(key):
        k = key if isinstance(key, str) else key.decode()
        if k == "status:birdnet":
            return json.dumps(
                {"service": "birdnet", "timestamp": time.time(), "status": "Running"}
            ).encode()
        if k == "status:uploader:myhost":
            return json.dumps(
                {
                    "service": "uploader",
                    "timestamp": time.time(),
                    "status": "Running",
                    "last_upload": time.time(),
                }
            ).encode()
        if k == "status:livesound:front":
            return json.dumps(
                {"service": "livesound", "timestamp": time.time(), "status": "Running"}
            ).encode()
        if k == "status:livesound:back":
            return json.dumps(
                {"service": "livesound", "timestamp": time.time(), "status": "Running"}
            ).encode()
        return None

    mock_redis.get.side_effect = get_side_effect

    # Mock Mailer
    mock_mailer = MagicMock()

    # Mock file writing for system_status.json (legacy)
    with patch("builtins.open", new_callable=MagicMock):
        # Run Check
        check_services_status(mock_mailer, {})

        # Verify call to write system_status.json
        # We find the call that writes to system_status.json
        # Note: Depending on impl, it might be the last call
        # We can inspect what was written to Redis or File.

        # Check Redis set call for system:status
        # Redis.set("system:status", json_dump)
        assert mock_redis.set.called
        args = mock_redis.set.call_args
        assert args[0][0] == "system:status"
        system_status = json.loads(args[0][1])

        # Check BirdNET (Legacy name)
        assert "birdnet" in system_status
        assert system_status["birdnet"]["status"] == "Running"

        # Check Uploader (New name)
        assert "uploader_myhost" in system_status
        assert system_status["uploader_myhost"]["status"] == "Running"

        # Check Livesound (Multiple)
        assert "livesound_front" in system_status
        assert "livesound_back" in system_status

        # Check Missing Service (e.g. Dashboard if we didn't mock it)
        # Dashboard is in SERVICES_CONFIG.
        assert "dashboard" in system_status
        assert system_status["dashboard"]["status"] == "Down"


def test_garbage_key_ignore(mock_redis):
    """Test that bad json is ignored."""
    mock_redis.keys.return_value = [b"status:birdnet", b"status:badjson"]

    def get_side_effect(key):
        k = key if isinstance(key, str) else key.decode()
        if k == "status:birdnet":
            return json.dumps(
                {"service": "birdnet", "timestamp": time.time(), "status": "Running"}
            ).encode()
        if k == "status:badjson":
            return b"{invalid_json"
        return None

    mock_redis.get.side_effect = get_side_effect

    mock_mailer = MagicMock()

    with patch("builtins.open", new_callable=MagicMock):
        check_services_status(mock_mailer, {})

        # Check logic
        args = mock_redis.set.call_args
        system_status = json.loads(args[0][1])

        assert "birdnet" in system_status
        assert "badjson" not in system_status
