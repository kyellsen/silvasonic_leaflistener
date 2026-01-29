import pytest


def test_gateway_root(gateway_client):
    """Verify that the root URL is accessible (proxies to Dashboard)."""
    try:
        response = gateway_client.get("/")
        # If Dashboard is behind auth, it redirects to /auth/login (302)
        assert response.status_code in [200, 302], (
            f"Root URL failed with status {response.status_code}"
        )
    except Exception as e:
        pytest.fail(f"Could not connect to Gateway: {e}")


def test_gateway_stats(gateway_client):
    """Verify that /stats route is accessible (proxies to Dashboard)."""
    response = gateway_client.get("/stats")
    assert response.status_code in [200, 302]


def test_gateway_static_assets(gateway_client):
    """Verify that static assets are potentially served (e.g. favicon)."""
    # Assuming standard dashboard has favicon or static dir
    # This is a loose check.
    response = gateway_client.get("/static/favicon.ico")
    # Might be 404 if not present, but 200 if present.
    # Just ensure we get *a* response, not connection error.
    assert response.status_code in [200, 404]


def test_gateway_server_header(gateway_client):
    """Verify (optional) that the server header identifies Caddy, or at least exists."""
    response = gateway_client.get("/")
    # Caddy usually sends 'Server: Caddy', unless hidden.
    assert "server" in response.headers or "Server" in response.headers
