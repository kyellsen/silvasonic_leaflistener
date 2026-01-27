import logging
import threading
import time

from flask import Flask, render_template, request
from wifi_manager import WifiManager

app = Flask(__name__)
manager = WifiManager()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webapp")


@app.route("/")
def index() -> str:
    """Render the index page with listed networks."""
    networks = manager.scan_networks()
    return str(render_template("index.html", networks=networks))


@app.route("/connect", methods=["POST"])
def connect() -> str | tuple[str, int]:
    """Handle the connection request to a WiFi network."""
    data = request.form
    ssid = data.get("ssid")
    password = data.get("password")

    if not ssid:
        return "SSID required", 400

    logger.info(f"Received connect request for {ssid}")

    def attempt_connect() -> None:
        time.sleep(3)  # Give browser time to load success page
        manager.connect_wifi(ssid, password)

    # Launch background thread
    threading.Thread(target=attempt_connect).start()

    # Assume success for now (we can't report failure easily if we disconnect)
    # Ideally we try to pre-validate, but wpa_supplicant handshakes take time.
    return str(render_template("success.html", ssid=ssid))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=False)
