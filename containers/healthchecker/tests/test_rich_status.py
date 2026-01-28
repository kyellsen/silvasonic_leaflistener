import json
import time
from unittest.mock import MagicMock, patch

from silvasonic_healthchecker.main import SERVICES_CONFIG, check_services_status
from silvasonic_healthchecker.models import ServiceConfig

# Mock SERVICES_CONFIG to include a test service
SERVICES_CONFIG["test_service"] = ServiceConfig(name="Test Service", timeout=60)


@patch("silvasonic_healthchecker.main.redis.Redis")
def test_rich_status_passthrough(mock_redis_cls, tmp_path):
    # Setup mock status directory (output)
    status_dir = tmp_path / "status"
    status_dir.mkdir()

    # Mock Redis return values
    mock_redis = mock_redis_cls.return_value
    mock_redis.keys.return_value = [b"status:test_service"]

    current_time = time.time()
    status_content = {
        "timestamp": current_time,
        "status": "Running",
        "message": "Processing Job #123",
        "state": "Processing",
    }
    mock_redis.get.return_value = json.dumps(status_content).encode("utf-8")

    # Mock Mailer
    mock_mailer = MagicMock()
    service_states = {}

    # Patch main.STATUS_DIR to point to our tmp_path
    with patch("silvasonic_healthchecker.main.STATUS_DIR", str(status_dir)):
        # Run the function
        check_services_status(mock_mailer, service_states)

    # Verify the output system_status.json
    system_status_file = status_dir / "system_status.json"
    assert system_status_file.exists()

    with open(system_status_file) as f:
        system_status = json.load(f)

    # Assertions
    assert "test_service" in system_status
    service_data = system_status["test_service"]

    # Crucial check: Message should be identifying processing job, NOT "Active"
    assert service_data["message"] == "Processing Job #123"
    assert service_data["state"] == "Processing"
    assert service_data["status"] == "Running"
