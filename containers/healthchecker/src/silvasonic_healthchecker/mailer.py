import json
import logging
import os

import apprise

logger = logging.getLogger("HealthChecker.Notifier")


class Mailer:
    def __init__(self) -> None:
        self.apobj = apprise.Apprise()
        self._configure_notifications()

    def _configure_notifications(self) -> None:
        """Configures Apprise with URLs from env vars or settings."""
        # 1. Load from settings.json (Preferred)
        config_path = "/config/settings.json"

        # We'll collect all valid URLs here
        urls = []

        # Check legacy environment variables first (Backward Compatibility)
        smtp_server = os.getenv("HEALTHCHECKER_SMTP_SERVER", "smtp.gmail.com")
        smtp_port = os.getenv("HEALTHCHECKER_SMTP_PORT", "465")
        smtp_user = os.getenv("HEALTHCHECKER_SMTP_USER")
        smtp_password = os.getenv("HEALTHCHECKER_SMTP_PASSWORD")
        recipient = os.getenv("HEALTHCHECKER_RECIPIENT_EMAIL")

        if os.path.exists(config_path):
            try:
                with open(config_path) as f:
                    settings = json.load(f)
                    hc_settings = settings.get("healthchecker", {})

                    # Allow overriding recipient from settings
                    if hc_settings.get("recipient_email"):
                        recipient = hc_settings.get("recipient_email")

                    # Allow adding generic Apprise URLs from settings
                    if hc_settings.get("apprise_urls"):
                        urls.extend(hc_settings.get("apprise_urls"))
            except Exception as e:
                logger.error(f"Failed to load settings override: {e}")

        # Construct Legacy Mailto URL if credentials exist
        if smtp_user and smtp_password and recipient:
            # Construct apprise mailto:// URL
            # Format: mailto://user:pass@domain:port?to=recipient
            # We need to extract domain from server if possible, or just use the server as is.
            # Apprise mailto parser is flexible.
            # If server is smtp.gmail.com, domain is gmail.com.
            # But we can just pass the server as the domain for custom SMTP usually.

            # Simplified logic: use the full server as the host.
            # Scheme: mailtos:// for SSL (465), mailto:// for others (TLs is context dependent but apprise handles likely)
            scheme = "mailtos" if str(smtp_port) == "465" else "mailto"

            # Encode special chars in user/pass if needed? Apprise handles basic, but let's just construct carefully.
            # Assuming standard chars for now.
            url = (
                f"{scheme}://{smtp_user}:{smtp_password}@{smtp_server}:{smtp_port}/?to={recipient}"
            )
            urls.append(url)
            logger.info(f"Added legacy SMTP notification for {recipient}")

        # Check for generic APPRISE_URLS env var (Comma separated)
        env_urls = os.getenv("APPRISE_URLS")
        if env_urls:
            urls.extend([u.strip() for u in env_urls.split(",") if u.strip()])

        # Add all to Apprise
        if not urls:
            logger.warning("No notification services configured.")
            return

        for url in urls:
            if self.apobj.add(url):
                # Mask sensitive info for logging
                masked_url = url.split("@")[-1] if "@" in url else "..."
                logger.info(f"Added notification service: ...@{masked_url}")
            else:
                logger.error(f"Failed to add notification URL: {url[:10]}...")

    def send_alert(self, subject: str, body: str) -> bool:
        """Sends an alert to all configured services. Returns True if at least one succeeded."""
        if not self.apobj:
            logger.warning("No notification backend configured.")
            return False

        try:
            # Apprise notify returns True if at least one notification was sent
            status = bool(
                self.apobj.notify(
                    body=body,
                    title=f"[Silvasonic] {subject}",
                )
            )

            if status:
                logger.info(f"Notification sent: {subject}")
            else:
                logger.error(f"Failed to send notification: {subject}")

            return status
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False
