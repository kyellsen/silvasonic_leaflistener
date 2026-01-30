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

    @staticmethod
    async def count_files_after(filename: str | None) -> int:
        """Counts how many files in REC_DIR are lexically 'after' the given filename."""

        def _count() -> int:
            if not os.path.exists(REC_DIR):
                return 0

            count = 0
            # Simple lexical scan. For huge directories, this might need optimizing (e.g. caching file lists)
            # But usually acceptable for < 100k files if cached periodically or directory listing is fast.
            # Using os.scandir for better performance
            try:
                # If filename provided, we only count files > filename
                # Filename strings usually "YYYY-MM-DD-HH-MM-SS.wav"

                check_val = os.path.basename(filename) if filename else ""

                with os.scandir(REC_DIR) as it:
                    for entry in it:
                        if entry.is_file() and entry.name.endswith((".wav", ".flac", ".mp3")):
                            if not check_val or entry.name > check_val:
                                count += 1
            except Exception as e:
                logger.error(f"Error counting files: {e}")
            return count

        return await run_in_executor(_count)

    @staticmethod
    async def get_recent_recordings(limit: int = 20) -> list[dict[str, Any]]:
        """Get list of most recent recordings from disk."""

        def _scan() -> list[dict[str, Any]]:
            if not os.path.exists(REC_DIR):
                return []

            files = []
            try:
                # We obtain top N files sorted by name desc (assuming timestamp naming)
                # Getting ALL files to sort might be heavy if folder is huge.
                # Assuming standard Silvasonic usage where older files are deleted/archived,
                # or we just accept the cost for now. optimizing with unix `ls -U` or similar logic
                # could be better but unsafe cross-platform.

                # Faster approach: os.scandir, collect all names, sort taking top N.
                entries = []
                with os.scandir(REC_DIR) as it:
                    for entry in it:
                        if entry.is_file() and entry.name.endswith((".wav", ".flac", ".mp3")):
                            # Store (name, size, mtime)
                            entries.append(
                                (entry.name, entry.stat().st_size, entry.stat().st_mtime)
                            )

                # Sort by name desc (newest first usually matches name)
                entries.sort(key=lambda x: x[0], reverse=True)
                top = entries[:limit]

                for name, size, mtime in top:
                    import datetime

                    dt = datetime.datetime.fromtimestamp(mtime)
                    files.append(
                        {
                            "filename": name,
                            "size_mb": round(size / (1024 * 1024), 2),
                            "created": dt.isoformat(),
                            # Mocking URL for now, dashboard/views handles actual logic or relies on static mounts
                            "url": f"/api/audio/{name}",
                        }
                    )
            except Exception as e:
                logger.error(f"Error getting recent recordings: {e}")
            return files

        return await run_in_executor(_scan)

    @staticmethod
    async def get_creation_rate(seconds: int = 10) -> int:
        """Returns number of files created in last N seconds."""
        import time

        def _rate() -> int:
            if not os.path.exists(REC_DIR):
                return 0

            count = 0
            cutoff = time.time() - seconds
            try:
                with os.scandir(REC_DIR) as it:
                    for entry in it:
                        if entry.is_file() and entry.name.endswith((".wav", ".flac", ".mp3")):
                            if entry.stat().st_mtime > cutoff:
                                count += 1
            except Exception:
                pass
            return count

        return await run_in_executor(_rate)
