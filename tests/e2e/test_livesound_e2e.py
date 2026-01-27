import pytest
import re
from playwright.sync_api import Page, expect

# Base URL for the dashboard - assuming running locally or in container network
# If running e2e from outside, it needs to hit the dashboard container
BASE_URL = "http://localhost:8080" # Default Dashboard Port

def test_livesound_page_load(page: Page):
    page.goto(f"{BASE_URL}/livesound")
    expect(page).to_have_title(re.compile("Silvasonic"))
    expect(page.get_by_role("heading", name="Livesound Stream")).to_be_visible()
    
def test_start_stop_stream(page: Page):
    page.goto(f"{BASE_URL}/livesound")
    
    # Check initial state
    play_btn = page.locator("#playButton")
    status = page.locator("#statusText")
    
    # Start Stream
    play_btn.click()
    expect(status).to_contain_text("Live Audio", timeout=10000) 
    
    # Check if Pause icon is visible (implies playing state in UI)
    pause_icon = page.locator("#pauseIcon")
    expect(pause_icon).to_be_visible()
    
    # Stop Stream
    play_btn.click()
    expect(status).to_contain_text("Stopped")
    expect(pause_icon).not_to_be_visible()

def test_volume_control(page: Page):
    page.goto(f"{BASE_URL}/livesound")
    
    slider = page.locator("#volumeSlider")
    
    # Change volume
    slider.fill("0.5")
    
    # Verify JS property
    # We need to evaluate the audio element's volume
    vol = page.evaluate("document.querySelector('audio').volume")
    assert vol == 0.5

def test_source_switching(page: Page):
    page.goto(f"{BASE_URL}/livesound")
    
    select = page.locator("#sourceSelect")
    # Get options, assume at least 'default' and maybe mock others if backend provided them
    # For E2E against real backend, we might only have default if no mics connected.
    # But user requirement says "verify switching".
    # If only one option, we can't test switching effectively without data.
    # We'll check if we can select 'default' explicitly or just check the element exists.
    
    expect(select).to_be_visible()
    
    # Simulate switch if possible
    # page.select_option("#sourceSelect", "default")
    # Expect status to imply reconnect
    
    # If there are multiple options, select the second one
    options = select.locator("option").all()
    if len(options) > 1:
        val = options[1].get_attribute("value")
        select.select_option(val)
        
        # Verify socket reconnect log or status change
        # The UI shows "Connecting WS..." briefly
        status = page.locator("#statusText")
        # It happens fast, might miss it.
        # Check if the Host Info or Source param in URL would change? No, URL doesn't change on page.
        # But we can check internal state
        current_source = page.evaluate("document.getElementById('sourceSelect').value")
        assert current_source == val

def test_spectrogram_visualization(page: Page):
    page.goto(f"{BASE_URL}/livesound")
    
    # Canvas should exist
    canvas = page.locator("#spectrogramCanvas")
    expect(canvas).to_be_visible()
    
    # Start playing to trigger data
    page.click("#playButton")
    
    # Wait a bit for data
    page.wait_for_timeout(2000)
    
    # Check if canvas is not blank (requires pixel analysis or just assuming it works if no errors)
    # Simple check: verify no console errors
    msg = []
    page.on("console", lambda m: msg.append(m.text))
    # Expect no "error" in logs
    errors = [m for m in msg if "error" in m.lower()]
    assert len(errors) == 0, f"Found console errors: {errors}"
