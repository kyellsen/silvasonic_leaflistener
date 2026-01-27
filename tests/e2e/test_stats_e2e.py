from playwright.sync_api import Page, expect


def test_birdstats_loads(page: Page) -> None:
    # Navigate to the stats page
    # Assuming the app is running on localhost:8080 or similar
    # In a real CI, base_url would be configured
    page.goto("http://localhost:8080/stats")

    # Check if Title exists
    expect(page.get_by_text("BirdStats")).to_be_visible()

    # Check if ApexCharts containers exist
    expect(page.locator("#dailyChart")).to_be_visible()
    expect(page.locator("#hourlyChart")).to_be_visible()

    # Check if charts actually rendered (ApexCharts adds SVG)
    # Give it a moment to render
    page.wait_for_selector("#dailyChart .apexcharts-canvas", timeout=5000)


def test_date_filter(page: Page) -> None:
    page.goto("http://localhost:8080/stats")

    # Set dates
    page.fill("input[name='start']", "2023-01-01")
    page.fill("input[name='end']", "2023-01-07")

    # Submit
    page.click("button[type='submit']")

    # Verify URL params
    assert "start=2023-01-01" in page.url
    assert "end=2023-01-07" in page.url
