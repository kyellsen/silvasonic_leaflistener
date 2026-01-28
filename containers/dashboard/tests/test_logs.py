import pytest
from fastapi.testclient import TestClient
from silvasonic_dashboard.auth import require_auth
from silvasonic_dashboard.main import app


# Override auth to bypass login for tests
async def mock_require_auth():
    return True


client = TestClient(app)


@pytest.fixture
def mock_auth():
    app.dependency_overrides[require_auth] = mock_require_auth
    yield
    app.dependency_overrides = {}


@pytest.fixture
def temp_log_dir(tmp_path, monkeypatch):
    """Point LOG_DIR to a temporary path for testing"""
    monkeypatch.setattr("silvasonic_dashboard.main.LOG_DIR", str(tmp_path))
    return tmp_path


def test_get_logs_success(mock_auth, temp_log_dir):
    """Test fetching logs for a valid service"""
    service_name = "test_service"
    log_content = "Line 1\nLine 2\nLine 3\n"

    # Create dummy log file
    log_file = temp_log_dir / f"{service_name}.log"
    log_file.write_text(log_content)

    response = client.get(f"/api/logs/{service_name}")
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert "Line 1" in data["content"]
    assert "Line 3" in data["content"]


def test_get_logs_not_found(mock_auth, temp_log_dir):
    """Test fetching logs for a non-existent service"""
    service_name = "ghost_service"

    response = client.get(f"/api/logs/{service_name}")
    assert response.status_code == 200
    data = response.json()
    assert "content" in data
    assert "not found" in data["content"].lower()


def test_get_logs_unauthorized():
    """Test endpoint without auth override"""
    # clear overrides just in case
    app.dependency_overrides = {}

    service_name = "any_service"
    response = client.get(f"/api/logs/{service_name}", allow_redirects=False)

    # Should be 401 or Redirect to login depending on implementation
    # The endpoint raises HTTPException(401) if auth fails (check main.py)
    # The depends(require_auth) usually redirects if HTML, but raises if API?
    # Logic in main.py: if isinstance(auth, RedirectResponse): raise HTTPException(401)

    assert response.status_code in [401, 302, 307]
