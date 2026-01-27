import json
import logging
import os
import typing
from pathlib import Path

import yaml

logger = logging.getLogger("Config")


class Config:
    def __init__(self) -> None:
        # Paths
        self.INPUT_DIR = Path(os.getenv("INPUT_DIR", "/data/recording"))
        self.RESULTS_DIR = Path(os.getenv("RESULTS_DIR", "/data/db/results"))
        self.CLIPS_DIR = self.RESULTS_DIR / "clips"
        self.CONFIG_FILE = Path(os.getenv("CONFIG_FILE", "/etc/birdnet/config.yml"))

        # Watcher
        self.RECURSIVE_WATCH = os.getenv("RECURSIVE_WATCH", "true").lower() == "true"

    def _load_yaml(self) -> dict[str, typing.Any]:
        """Loads the YAML config file if it exists, otherwise returns empty dict."""
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE) as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Failed to load config file {self.CONFIG_FILE}: {e}")
                return {}
        return {}

    @property
    def birdnet_settings(self) -> dict[str, typing.Any]:
        """Returns a dictionary of BirdNET settings, merging defaults,
        env vars, and YAML config.
        Priority: settings.json (BirdNET) > settings.json (Global Location) > config.yaml > Environment > Default
        """
        yaml_conf = self._load_yaml().get("birdnet", {})
        full_json = self._load_settings_json()
        json_conf = full_json.get("birdnet", {})
        location_conf = full_json.get("location", {})

        # Helper to get value from JSON -> YAML -> Env -> Default
        def get_val(
            key: str,
            env_key: str,
            default: typing.Any,
            type_cast: typing.Callable[[typing.Any], typing.Any],
        ) -> typing.Any:
            # 1. Dashboard Settings (JSON)
            val = json_conf.get(key)
            if val is not None:
                return type_cast(val)

            # 1.5 Special Fallback for Location (Global Settings)
            if key == "latitude" and "latitude" in location_conf:
                return type_cast(location_conf["latitude"])
            if key == "longitude" and "longitude" in location_conf:
                return type_cast(location_conf["longitude"])

            # 2. Static Config (YAML)
            val = yaml_conf.get(key)
            if val is not None:
                return type_cast(val)

            # 3. Environment Variable
            val = os.getenv(env_key)
            if val is not None:
                return type_cast(val)

            # 4. Default
            return default

        return {
            "min_conf": get_val("min_confidence", "MIN_CONFIDENCE", 0.7, float),
            "lat": get_val("latitude", "LATITUDE", -1, float),
            "lon": get_val("longitude", "LONGITUDE", -1, float),
            "week": get_val("week", "WEEK", -1, int),
            "overlap": get_val("overlap", "OVERLAP", 0.0, float),
            "sensitivity": get_val("sensitivity", "SENSITIVITY", 1.0, float),
            "threads": get_val("threads", "THREADS", 3, int),
        }

    def _load_settings_json(self) -> dict[str, typing.Any]:
        """Loads the shared JSON settings file."""
        settings_path = Path("/config/settings.json")
        if settings_path.exists():
            try:
                with open(settings_path) as f:
                    return typing.cast(dict[str, typing.Any], json.load(f))
            except Exception as e:
                logger.error(f"Failed to load settings.json: {e}")
        return {}

    # Backward compatibility properties (proxies to fresh settings)
    @property
    def MIN_CONFIDENCE(self) -> float:
        return float(self.birdnet_settings["min_conf"])

    @property
    def LATITUDE(self) -> float:
        return float(self.birdnet_settings["lat"])

    @property
    def LONGITUDE(self) -> float:
        return float(self.birdnet_settings["lon"])

    @property
    def WEEK(self) -> int:
        return int(self.birdnet_settings["week"])

    @property
    def OVERLAP(self) -> float:
        return float(self.birdnet_settings["overlap"])

    @property
    def SENSITIVITY(self) -> float:
        return float(self.birdnet_settings["sensitivity"])

    @property
    def THREADS(self) -> int:
        return int(self.birdnet_settings["threads"])


config = Config()
