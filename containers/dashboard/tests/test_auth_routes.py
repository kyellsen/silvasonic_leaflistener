from fastapi.testclient import TestClient
from silvasonic_dashboard import auth
from silvasonic_dashboard.main import app

client = TestClient(app)


def test_dev_login_success(monkeypatch):
    """Test that dev login works in development mode."""
    # Patch the constant in the auth module
    monkeypatch.setattr(auth, "SILVASONIC_ENV", "development")

    response = client.post("/auth/dev-login", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == "/dashboard"
    assert auth.COOKIE_NAME in response.cookies


def test_dev_login_forbidden_in_prod(monkeypatch):
    """Test that dev login is forbidden in production mode."""
    # Patch the constant in the auth module
    monkeypatch.setattr(auth, "SILVASONIC_ENV", "production")

    response = client.post("/auth/dev-login", follow_redirects=False)

    assert response.status_code == 403
