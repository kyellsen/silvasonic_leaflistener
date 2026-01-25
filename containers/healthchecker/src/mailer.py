import smtplib
import os
import logging
from email.message import EmailMessage

logger = logging.getLogger("HealthChecker.Mailer")

class Mailer:
    def __init__(self):
        self.smtp_server = os.getenv("HEALTHCHECKER_SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("HEALTHCHECKER_SMTP_PORT", 465))
        self.smtp_user = os.getenv("HEALTHCHECKER_SMTP_USER")
        self.smtp_password = os.getenv("HEALTHCHECKER_SMTP_PASSWORD")
        self.recipient = os.getenv("HEALTHCHECKER_RECIPIENT_EMAIL")
        
        # Load overrides from settings.json
        config_path = "/config/settings.json"
        if os.path.exists(config_path):
            try:
                import json
                with open(config_path, 'r') as f:
                    settings = json.load(f)
                    hc_settings = settings.get("healthchecker", {})
                    
                    # Override if present and not empty
                    if hc_settings.get("recipient_email"):
                        self.recipient = hc_settings.get("recipient_email")
                        logger.info(f"Using recipient override: {self.recipient}")
                        
                    # Future: Allow overriding SMTP creds too if needed, but risky for security (plaintext in json)
            except Exception as e:
                logger.error(f"Failed to load settings override: {e}")

    def send_alert(self, subject: str, body: str) -> bool:
        """Sends an email alert. Returns True if successful."""
        if not self.smtp_user or not self.smtp_password or not self.recipient:
            logger.error("SMTP credentials or recipient not configured. Cannot send email.")
            return False

        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = f"[Silvasonic Alert] {subject}"
        msg['From'] = self.smtp_user
        msg['To'] = self.recipient

        try:
            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
            
            logger.info(f"Email sent to {self.recipient}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
