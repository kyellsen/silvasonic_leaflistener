import os

import pytest
import requests
from playwright.sync_api import Page

# Get base URL from environment or default
# This allows the shell script to override it, or uses localhost as default for IDE execution
DEFAULT_BASE_URL = "http://localhost:8080"


@pytest.fixture(scope="session")
def base_url() -> str:
    """Return the base URL for the application under test."""
    return os.getenv("E2E_BASE_URL", DEFAULT_BASE_URL)


@pytest.fixture(autouse=True)
def check_service_health(base_url: str) -> None:
    """
    Optional: Check if service is up before running tests.
    This creates a fast fail if the server isn't running.
    """
    # specific endpoint to check? or just root
    try:
        resp = requests.get(base_url, timeout=2)
        if resp.status_code >= 500:
            pytest.warns(UserWarning, f"Target {base_url} returned status {resp.status_code}")
    except requests.ConnectionError:
        pytest.fail(f"Could not connect to {base_url}. Is the server running?")


@pytest.fixture
def dashboard(page: Page, base_url: str) -> Page:
    """
    A page fixture that is already navigated to the dashboard home.
    """
    page.goto(base_url)
    return page
