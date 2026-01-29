# This is a forced overwrite update to ensure the file inside the container
# (which should be mounted from here) matches our expectation.

import json
import os
from typing import Any, cast

import redis
from async_lru import alru_cache

from .common import REC_DIR, logger, run_in_executor


class RecorderService:
    @staticmethod
    def get_audio_settings(profile: dict[str, Any] | None) -> float:
        """Extract audio BPS (Bytes per Second) from profile."""
        try:
            if isinstance(profile, dict) and "audio" in profile:
                audio = profile["audio"]
                sr = int(audio.get("sample_rate", 48000))
                ch = int(audio.get("channels", 1))
                depth = int(audio.get("bit_depth", 16))

                # Bytes per second (Uncompressed)
                return sr * ch * (depth / 8)
        except Exception:
            pass
        return 48000 * 1 * 2  # Default to 48kHz, Mono, 16-bit (96000 Bps)

    @staticmethod
    @alru_cache(ttl=1)
    async def get_status() -> list[dict[str, Any]]:
        """Returns a list of status dicts for all detected recorders from Redis."""
        statuses = []
        try:
            # Connect to Redis
            r: redis.Redis = redis.Redis(
                host="silvasonic_redis", port=6379, db=0, socket_connect_timeout=1
            )

            # Find all recorder keys
            keys = cast(list[bytes], r.keys("status:recorder:*"))

            # Additional keys that might match: "status:recorder"
            if r.exists("status:recorder"):
                keys.append(b"status:recorder")

            if not keys:
                return []

            for key in keys:
                try:
                    raw_data = cast(bytes | None, r.get(key))
                    if not raw_data:
                        continue

                    data = json.loads(raw_data)
                    meta = data.get("meta", {})
                    profile = meta.get("profile", {})

                    # 1. Device Name Cleaning
                    raw_device = meta.get("device", "Unknown")
                    clean_device = raw_device
                    if isinstance(raw_device, str):
                        import re

                        match = re.search(r"\[(.*?)\]", raw_device)
                        if match:
                            clean_device = match.group(1)

                    data["profile"] = profile
                    data["device"] = clean_device
                    data["device_raw"] = raw_device

                    # 2. Storage Forecast
                    forecast = {
                        "daily_gb": 0,
                        "daily_str": "Unknown",
                        "remaining_days": 0,
                        "remaining_str": "Unknown",
                    }

                    if isinstance(profile, dict) and "audio" in profile:
                        try:
                            bps = RecorderService.get_audio_settings(profile)
                            compression = 0.6
                            bytes_per_day = bps * 60 * 60 * 24 * compression
                            gb_per_day = bytes_per_day / (1024**3)

                            forecast["daily_gb"] = round(gb_per_day, 1)
                            forecast["daily_str"] = f"~{gb_per_day:.1f} GB"

                            # Calculate Remaining using shutil on the recording path
                            import shutil

                            def get_usage() -> tuple[int, int, int]:
                                check_path = REC_DIR if os.path.exists(REC_DIR) else "/"
                                u = shutil.disk_usage(check_path)
                                return u.total, u.used, u.free

                            _, _, free_bytes = await run_in_executor(get_usage)

                            if bytes_per_day > 0:
                                days_remaining = free_bytes / bytes_per_day
                                forecast["remaining_days"] = int(days_remaining)
                                if days_remaining > 365:
                                    forecast["remaining_str"] = ">1y"
                                else:
                                    forecast["remaining_str"] = f"~{int(days_remaining)}d"

                        except Exception as e:
                            logger.error(f"Forecast Error: {e}")

                    data["storage_forecast"] = forecast
                    statuses.append(data)
                except Exception as e:
                    logger.error(
                        f"Error reading redis key {key.decode('utf-8', errors='replace')}: {e}"
                    )

            statuses.sort(key=lambda x: x.get("profile", {}).get("name", ""))
            return statuses

        except Exception as e:
            logger.error(f"Recorder status error: {e}")

        # Fallback in case of Critical Error (e.g. Redis down), but ideally [] if just empty
        return []
