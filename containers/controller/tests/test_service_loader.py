import os
import tempfile

import pytest
import yaml
from silvasonic_controller.podman_client import PodmanOrchestrator
from silvasonic_controller.service_manager import ServiceManager


# Mock Orchestrator
class MockOrchestrator(PodmanOrchestrator):
    def __init__(self):
        pass


@pytest.fixture
def mock_orchestrator():
    return MockOrchestrator()


def test_load_valid_config(mock_orchestrator):
    config_data = {
        "services": {
            "test_service": {
                "image": "test-image:latest",
                "enabled": True,
                "restart_policy": "on-failure",
                "env": {"FOO": "bar"},
                "mounts": [{"source": "/host/path", "target": "/container/path", "mode": "ro"}],
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
        yaml.dump(config_data, tmp)
        tmp_path = tmp.name

    try:
        manager = ServiceManager(mock_orchestrator, config_path=tmp_path)
        assert "test_service" in manager._services
        service = manager._services["test_service"]
        assert service.image == "test-image:latest"
        assert service.restart_policy == "on-failure"
        assert service.env["FOO"] == "bar"
        assert len(service.mounts) == 1
        assert service.mounts[0].source == "/host/path"
    finally:
        os.remove(tmp_path)


def test_load_invalid_config_missing_field(mock_orchestrator):
    config_data = {
        "services": {
            "bad_service": {
                "enabled": True
                # Missing image
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
        yaml.dump(config_data, tmp)
        tmp_path = tmp.name

    try:
        # Should catch validation error and log it, resulting in empty services (or partial if we handled it per service)
        # Current implementation fails whole file load on root validation error
        manager = ServiceManager(mock_orchestrator, config_path=tmp_path)
        assert "bad_service" not in manager._services
    finally:
        os.remove(tmp_path)


def test_load_default_values(mock_orchestrator):
    config_data = {"services": {"minimal_service": {"image": "minimal:latest"}}}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
        yaml.dump(config_data, tmp)
        tmp_path = tmp.name

    try:
        manager = ServiceManager(mock_orchestrator, config_path=tmp_path)
        service = manager._services["minimal_service"]
        assert service.enabled is True
        assert service.restart_policy == "always"
        assert service.network == "silvasonic_default"
        assert service.env == {}
        assert service.mounts == []
    finally:
        os.remove(tmp_path)
