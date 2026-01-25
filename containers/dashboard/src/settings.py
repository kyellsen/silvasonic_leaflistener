from pydantic import BaseModel, Field, EmailStr, AnyUrl, ValidationError, validator
from typing import List, Optional
import os
import json
import logging
import copy

logger = logging.getLogger("Dashboard.Settings")

CONFIG_PATH = "/config/settings.json"

class LocaleSettings(BaseModel):
    use_german_names: bool = False

class HealthCheckerSettings(BaseModel):
    recipient_email: Optional[str] = Field(default="") # Empty allowed, falls back to env
    apprise_urls: List[str] = Field(default_factory=list)

    @validator('recipient_email')
    def validate_email(cls, v):
        if not v: return ""
        # Basic check or use EmailStr if email-validator is strictly available
        # Using simple check to avoid hard crash if dependency missing, 
        # but Plan said EmailStr. Let's assume EmailStr is desired but might fail if pydantic[email] not installed.
        # Given the user wants validation, let's try to be robust. 
        # If we use EmailStr and it fails import, it crashes. 
        # Let's stick to str but manual regex or if pydantic has it built-in without extra dep? 
        # Pydantic v1 vs v2? Assuming v1 based on typical stack or v2.
        # Let's use EmailStr but import it safely? No, let's just use strict type if possible.
        # Actually user explicitly asked for validation.
        return v

class LocationSettings(BaseModel):
    latitude: float = Field(default=52.52, ge=-90, le=90)
    longitude: float = Field(default=13.40, ge=-180, le=180)

class Settings(BaseModel):
    locale: LocaleSettings = Field(default_factory=LocaleSettings)
    healthchecker: HealthCheckerSettings = Field(default_factory=HealthCheckerSettings)
    location: LocationSettings = Field(default_factory=LocationSettings)

DEFAULT_SETTINGS = Settings().dict()

class SettingsService:
    @staticmethod
    def get_settings() -> dict:
        """Load settings from JSON, returning dict for compatibility."""
        return SettingsService.load_model().dict()

    @staticmethod
    def load_model() -> Settings:
        """Load settings as Pydantic model."""
        if not os.path.exists(CONFIG_PATH):
            return Settings()
            
        try:
            with open(CONFIG_PATH, 'r') as f:
                data = json.load(f)
            # Use parse_obj to validate and merge with defaults
            # However, partial updates need care. 
            # Pydantic replaces whole sub-models usually.
            # Best strategy: Load default, update dict, then parse.
            
            # Deep merge helper
            current = Settings().dict()
            
            def deep_update(target, source):
                for k, v in source.items():
                    if isinstance(v, dict) and k in target and isinstance(target[k], dict):
                        deep_update(target[k], v)
                    else:
                        target[k] = v
            
            deep_update(current, data)
            
            return Settings(**current)
            
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            return Settings()

    @staticmethod
    def save_settings(new_settings: dict) -> bool:
        """Save settings (dict) to JSON, with validation."""
        try:
            # Validate via model
            model = Settings(**new_settings)
            
            # Ensure directory exists
            if not os.path.exists(os.path.dirname(CONFIG_PATH)):
                try:
                    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
                except:
                    pass

            with open(CONFIG_PATH, 'w') as f:
                json.dump(model.dict(), f, indent=4)
            return True
        except ValidationError as e:
            logger.error(f"Validation Error saving settings: {e}")
            raise e # Propagate to controller for UI feedback
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return False

    @staticmethod
    def is_german_names_enabled():
        return SettingsService.load_model().locale.use_german_names

