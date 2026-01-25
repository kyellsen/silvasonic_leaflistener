import os
import json
import logging
import copy

logger = logging.getLogger("Dashboard.Settings")

CONFIG_PATH = "/config/settings.json"

DEFAULT_SETTINGS = {
    "locale": {
        "use_german_names": False
    },
    # HealthChecker overrides (stored here, read by HealthChecker)
    "healthchecker": {
        "recipient_email": "" # Empty means use ENV fallback
    },
    "location": {
        "latitude": 52.52,
        "longitude": 13.40
    }
}

class SettingsService:
    @staticmethod
    def get_settings():
        """Load settings from JSON, returning defaults for missing keys."""
        if not os.path.exists(CONFIG_PATH):
            return copy.deepcopy(DEFAULT_SETTINGS)
            
        try:
            with open(CONFIG_PATH, 'r') as f:
                data = json.load(f)
                
            # Merge with defaults (shallow merge for sections)
            settings = copy.deepcopy(DEFAULT_SETTINGS)
            
            # Deep merge manually for known sections
            if "locale" in data:
                settings["locale"].update(data["locale"])
            if "healthchecker" in data:
                settings["healthchecker"].update(data["healthchecker"])
            if "location" in data:
                settings["location"].update(data["location"])
                
            return settings
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            return copy.deepcopy(DEFAULT_SETTINGS)

    @staticmethod
    def save_settings(new_settings: dict):
        """Save settings to JSON."""
        # Ensure directory exists (container /config should be mapped)
        if not os.path.exists(os.path.dirname(CONFIG_PATH)):
            # Should not happen if volume is mounted, but just in case
            try:
                os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            except:
                pass

        try:
            with open(CONFIG_PATH, 'w') as f:
                json.dump(new_settings, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return False

    @staticmethod
    def is_german_names_enabled():
        return SettingsService.get_settings().get("locale", {}).get("use_german_names", False)
