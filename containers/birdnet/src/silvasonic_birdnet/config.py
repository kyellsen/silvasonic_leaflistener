import json
import logging
import os
import typing
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("Config")


class BirdNETParameters(BaseModel):
    """
    Specific parameters for the BirdNET analysis.
    """

    min_conf: float = Field(default=0.7, ge=0.0, le=1.0)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    week: int = Field(default=-1, ge=-1, le=53)
    overlap: float = Field(default=0.0, ge=0.0, le=3.0)
    sensitivity: float = Field(default=1.0, ge=0.5, le=1.5)
    threads: int = Field(default=3, ge=1)


class Settings(BaseSettings):
    """
    Main container configuration.
    """

    model_config = SettingsConfigDict(case_sensitive=True)

    # Paths (Env vars or defaults)
    INPUT_DIR: Path = Field(default=Path("/data/recording"), alias="INPUT_DIR")
    RESULTS_DIR: Path = Field(default=Path("/data/db/results"), alias="RESULTS_DIR")
    CLIPS_DIR: Path | None = Field(default=None, validate_default=False)  # Computed in __init__

    # Config Files
    CONFIG_FILE: Path = Field(default=Path("/etc/birdnet/config.yml"), alias="CONFIG_FILE")
    SETTINGS_JSON: Path = Field(default=Path("/config/settings.json"))

    # Watcher
    RECURSIVE_WATCH: bool = Field(default=True, alias="RECURSIVE_WATCH")

    # The actual BirdNET parameters (loaded from files/env)
    birdnet: BirdNETParameters = Field(default_factory=lambda: BirdNETParameters())

    def model_post_init(self, __context: typing.Any) -> None:
        """Calculate derived paths and load detailed BirdNET config."""
        if self.CLIPS_DIR is None:
            self.CLIPS_DIR = self.RESULTS_DIR / "clips"

        # Load and merge BirdNET parameters
        self.reload_birdnet_config()

    def reload_birdnet_config(self) -> None:
        """
        Loads the BirdNET parameters with the following priority:
        1. settings.json (BirdNET section)
        2. settings.json (Global Location for lat/lon fallback)
        3. config.yml
        4. Environment Variables
        5. Defaults (defined in BirdNETParameters)
        """
        try:
            # 1. Start with Empty Dict/Defaults
            # We'll build a dict of values to pass to BirdNETParameters

            # 4. Environment Variables (Low Priority, but we read them first to be overridden?
            # No, standard is Env > File. But here we have specific hierarchy requirements)
            # The original code had: JSON > YAML > Env > Default.

            # Let's collect values.

            # --- Defaults are in the Model ---

            # --- Environment ---
            env_values: dict[str, typing.Any] = {}
            if os.getenv("MIN_CONFIDENCE"):
                env_values["min_conf"] = float(os.getenv("MIN_CONFIDENCE"))  # type: ignore
            if os.getenv("LATITUDE"):
                env_values["lat"] = float(os.getenv("LATITUDE"))  # type: ignore
            if os.getenv("LONGITUDE"):
                env_values["lon"] = float(os.getenv("LONGITUDE"))  # type: ignore
            if os.getenv("WEEK"):
                env_values["week"] = int(os.getenv("WEEK"))  # type: ignore
            if os.getenv("OVERLAP"):
                env_values["overlap"] = float(os.getenv("OVERLAP"))  # type: ignore
            if os.getenv("SENSITIVITY"):
                env_values["sensitivity"] = float(os.getenv("SENSITIVITY"))  # type: ignore
            if os.getenv("THREADS"):
                env_values["threads"] = int(os.getenv("THREADS"))  # type: ignore

            # --- YAML ---
            yaml_values: dict[str, typing.Any] = {}
            if self.CONFIG_FILE.exists():
                try:
                    with open(self.CONFIG_FILE) as f:
                        data = yaml.safe_load(f) or {}
                        yaml_section = data.get("birdnet", {})
                        # Map YAML keys to Model keys if they differ
                        # YAML keys assumed same as model for simplicity, or map here.
                        # Original code: `yaml_conf.get(key)` where key is model field name.
                        yaml_values = yaml_section
                        if "min_confidence" in yaml_values:
                            yaml_values["min_conf"] = yaml_values.pop("min_confidence")
                except Exception as e:
                    logger.error(f"Failed to load config.yml: {e}")

            # --- JSON ---
            json_birdnet: dict[str, typing.Any] = {}
            json_location: dict[str, typing.Any] = {}
            if self.SETTINGS_JSON.exists():
                try:
                    with open(self.SETTINGS_JSON) as f:
                        data = json.load(f) or {}
                        json_birdnet = data.get("birdnet", {})
                        json_location = data.get("location", {})
                except Exception as e:
                    logger.error(f"Failed to load settings.json: {e}")

            # --- Merging Strategy ---
            # We want JSON > YAML > Env > Default
            # We construct the final dict by overlaying.

            final_values: dict[str, typing.Any] = {}

            # 1. Env (Base)
            final_values.update(env_values)

            # 2. YAML (Overwrites Env)
            # Filter yaml_values to only known keys to avoid garbage?
            # Pydantic ignores extras by default (or we can set extra='ignore')
            final_values.update(yaml_values)

            # 3. JSON Location (Special Fallback)
            # If lat/lon NOT in json_birdnet, use json_location
            # Actually original code: use json_birdnet first.

            # 4. JSON BirdNET (Highest Priority)
            # We need to map keys:
            # "min_confidence" -> "min_conf"
            # "latitude" -> "lat"
            # "longitude" -> "lon"

            # Helper to map and update
            def update_if_exists(
                target: dict[str, typing.Any],
                source: dict[str, typing.Any],
                source_key: str,
                target_key: str,
            ) -> None:
                if source_key in source and source[source_key] is not None:
                    target[target_key] = source[source_key]

            # Global Location Fallback (if not present so far? No, Global Loc overrides YAML/Env but under BirdNET specific)
            # This is tricky.
            # Original: logic was `get_val` called for each key.
            #   val = json_conf.get(key) -> Returns if found.
            #   if key=="lat" and "latitude" in location: return
            #   val = yaml_conf.get(key)
            #   val = env

            # So: JSON_BirdNET > JSON_Location > YAML > Env

            # Let's apply JSON Location first
            update_if_exists(final_values, json_location, "latitude", "lat")
            update_if_exists(final_values, json_location, "longitude", "lon")

            # Then JSON BirdNET
            update_if_exists(final_values, json_birdnet, "min_confidence", "min_conf")
            update_if_exists(final_values, json_birdnet, "latitude", "lat")
            update_if_exists(final_values, json_birdnet, "longitude", "lon")
            update_if_exists(final_values, json_birdnet, "week", "week")
            update_if_exists(final_values, json_birdnet, "overlap", "overlap")
            update_if_exists(final_values, json_birdnet, "sensitivity", "sensitivity")
            update_if_exists(final_values, json_birdnet, "threads", "threads")

            # Create/Validate Model
            self.birdnet = BirdNETParameters(**final_values)
            logger.info(f"Loaded BirdNET Config: {self.birdnet}")

        except ValidationError as e:
            logger.error(f"Configuration Validation Failed: {e}")
            # Fallback to default safely? Or crash?
            # Ideally crash to warn user, but for robustness we might keep default.
            # But the 'default_factory' is already set.
            # If we fail here, self.birdnet is NOT updated (keeps default).

    # Properties for backward compatibility (optional, but requested by plan to support analyzer.py changes)
    # Actually plan says "Update analyzer.py to use new typed config"
    # So we don't need properties here.


# Singleton Instance
config = Settings()
