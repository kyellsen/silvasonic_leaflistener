from playwright.sync_api import Page, expect

# Config
BASE_URL = "http://localhost:8080"  # Dashboard Port
# We assume the user has logged in or we mock auth?
# Dashboard redirects to /auth/login if not logged in.
# Credentials are in .env usually, but default is admin/silvasonic


def login(page: Page):
    """Log in to the dashboard."""
    page.goto(f"{BASE_URL}/auth/login")
    if "login" in page.url:
        page.fill("input[name='username']", "admin")
        page.fill("input[name='password']", "silvasonic")  # Default
        page.click("button[type='submit']")
        # Wait for redirect
        page.wait_for_url(f"{BASE_URL}/dashboard")


def test_dashboard_access(page: Page):
    """Smoke test: Can we see the dashboard?"""
    login(page)
    expect(page).to_have_title("Silvasonic Dashboard")
    expect(page.locator("h1").first).to_contain_text("Overview")


def test_livesound_page_elements(page: Page):
    """Check if LiveSound page loads without error and canvas is present."""
    login(page)
    page.click("a[href='/livesound']")
    expect(page).to_have_url(f"{BASE_URL}/livesound")

    # Check for Canvas (Spectrogram)
    canvas = page.locator("canvas#spectrogram")
    expect(canvas).to_be_visible()

    # Check for Status Label
    expect(page.locator("text=System:")).to_be_visible()


def test_settings_integrity(page: Page):
    """Check if Settings page renders forms correctly (Regression check)."""
    login(page)
    page.click("a[href='/settings']")

    # Check Latitude/Longitude inputs exist
    expect(page.locator("input[name='latitude']")).to_be_visible()
    expect(page.locator("input[name='longitude']")).to_be_visible()

    # Check Save button
    expect(page.locator("button:has-text('Save Settings')")).to_be_visible()
