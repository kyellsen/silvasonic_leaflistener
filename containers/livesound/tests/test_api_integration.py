from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from silvasonic_livesound.live.server import app, processor

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_sockets():
    """Mock socket operations to prevent real network binding during tests."""
    with patch("socket.socket") as mock:
        yield mock


@pytest.fixture(autouse=True)
def clean_processor():
    """Reset processor state before each test."""
    processor.stop()
    processor.sockets.clear()
    processor.source_ports.clear()
    processor.metrics.clear()

    # We must also clear the threads dict to avoid start() skipping them
    processor.threads.clear()


def test_source_lifecycle():
    # 1. Initial State: Empty
    response = client.get("/sources")
    assert response.status_code == 200
    assert response.json() == []

    # 2. Add Source
    new_source = {"name": "test_mic", "port": 12345}
    response = client.post("/sources", json=new_source)
    assert response.status_code == 200
    assert response.json() == {"status": "added", "name": "test_mic"}

    # 3. Verify Added
    response = client.get("/sources")
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "test_mic"
    assert data[0]["port"] == 12345
    assert not data[0]["active"]  # Not running loop in test
    assert data[0]["rms_db"] == -100.0

    # 4. Remove Source
    response = client.delete("/sources/test_mic")
    assert response.status_code == 200

    # 5. Verify Removed
    response = client.get("/sources")
    assert response.json() == []


def test_stream_endpoints_smoke():
    # Check if endpoints exist (not logic, just routing)
    response = client.get("/")
    assert response.status_code == 200
    assert "Silvasonic" in response.text
