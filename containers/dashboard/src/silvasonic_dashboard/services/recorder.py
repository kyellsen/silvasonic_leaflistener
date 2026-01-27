import datetime
import json
import os
import time
from datetime import UTC
from typing import Any

from async_lru import alru_cache

from .common import REC_DIR, STATUS_DIR, logger, run_in_executor


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

        return 48000 * 1 * 2  # Default to 48kHz, Mono, 16-bit (96000 Bps)

    @staticmethod
    @alru_cache(ttl=30)
    async def get_status() -> list[dict[str, Any]]:
        """Returns a list of status dicts for all detected recorders."""
        statuses = []
        try:
            import glob

            # blocking IO -> thread pool
            def scan_status_files() -> list[str]:
                files = glob.glob(os.path.join(STATUS_DIR, "recorder_*.json"))
                if os.path.exists(os.path.join(STATUS_DIR, "recorder.json")):
                    files.append(os.path.join(STATUS_DIR, "recorder.json"))
                return list(set(files))

            files = await run_in_executor(scan_status_files)

            if not files:
                return [
                    {
                        "status": "Unknown",
                        "profile": "No Recorders Found",
                        "device": "Unknown",
                        "storage_forecast": {"daily_str": "?", "remaining_str": "?"},
                    }
                ]

            for status_file in files:
                try:

                    def read_json(path: str) -> dict[str, Any]:
                        with open(path) as f:
                            return json.load(f)

                    data = await run_in_executor(read_json, status_file)

                    # Flatten meta for compatibility or just return rich data
                    meta = data.get("meta", {})
                    profile = meta.get("profile", {})

                    # 1. Device Name Cleaning
                    raw_device = meta.get("device", "Unknown")
                    clean_device = raw_device
                    if isinstance(raw_device, str):
                        # Extract content between first [] if present
                        # Example: card 0: r0 [UltraMic384K_EVO 16bit r0], device 0...
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
                    logger.error(f"Error reading {status_file}: {e}")

            # Sort by profile name or slug for stability
            statuses.sort(key=lambda x: x.get("profile", {}).get("name", ""))
            return statuses

        except Exception as e:
            logger.error(f"Recorder status error: {e}")

        return [
            {
                "status": "Unknown",
                "profile": "Error",
                "device": "Unknown",
                "storage_forecast": {"daily_str": "?", "remaining_str": "?"},
            }
        ]

    @staticmethod
    @alru_cache(ttl=30)
    async def get_recent_recordings(limit_per_source: int = 20) -> dict[str, list[dict[str, Any]]]:
        """Returns recordings grouped by source (folder name)."""
        grouped_recordings: dict[str, list[dict[str, Any]]] = {}

        try:
            # Get current BPS setting from first status for duration fallback
            statuses = await RecorderService.get_status()
            current_bps: float = 48000.0 * 2
            if statuses and "profile" in statuses[0]:
                current_bps = RecorderService.get_audio_settings(statuses[0]["profile"])

            if not os.path.exists(REC_DIR):
                return {}

            # Structure: REC_DIR / {source_id} / {file}.flac
            # Or REC_DIR / {file}.flac (legacy/default)

            # 1. Identify Sources (Directories)
            def list_dirs() -> list[str]:
                return [d for d in os.listdir(REC_DIR) if os.path.isdir(os.path.join(REC_DIR, d))]

            sources = await run_in_executor(list_dirs)
            if not sources:
                # Check for files in root (Default source)
                sources = ["Default"]

            # Helper to process a directory
            async def scan_source_async(source_name: str, path: str) -> list[dict[str, Any]]:
                def _scan() -> list[dict[str, Any]]:
                    items = []
                    try:
                        # Scan files
                        with os.scandir(path) as it:
                            for entry in it:
                                if entry.is_file() and entry.name.endswith(
                                    (".flac", ".wav", ".mp3")
                                ):
                                    try:
                                        stats = entry.stat()
                                        dt = datetime.datetime.fromtimestamp(stats.st_mtime)
                                        size_bytes = stats.st_size
                                        size_mb = round(size_bytes / (1024 * 1024), 2)

                                        # Duration Estimate
                                        duration = 0.0
                                        if size_bytes > 0:
                                            duration = size_bytes / (current_bps * 0.6)

                                        items.append(
                                            {
                                                "filename": entry.name,
                                                "file_size_bytes": size_bytes,
                                                "size_mb": size_mb,
                                                "formatted_time": dt.strftime("%Y-%m-%d %H:%M:%S"),
                                                "created_at_iso": dt.isoformat(),
                                                "duration_str": f"{duration:.2f}s",
                                                "duration_sec": duration,
                                                "source": source_name,
                                                "audio_relative_path": os.path.join(
                                                    source_name, entry.name
                                                )
                                                if source_name != "Default"
                                                else entry.name,
                                                "mtime": stats.st_mtime,
                                            }
                                        )
                                    except Exception:
                                        pass
                    except Exception as e:
                        logger.error(f"Error scanning source {source_name}: {e}")

                    # Sort by mtime DESC
                    items.sort(key=lambda x: float(str(x.get("mtime", 0))), reverse=True)
                    return items[:limit_per_source]

                return await run_in_executor(_scan)

            # 2. Process Sources
            # Check Root first (Legacy/Default)
            root_files = await scan_source_async("Default", REC_DIR)
            if root_files:
                grouped_recordings["Default"] = root_files

            # Check Subdirectories
            # Actually, scan_source above scans the path we give it.
            # If we identified real directories, scan them.
            def list_real_sources() -> list[str]:
                return [d for d in os.listdir(REC_DIR) if os.path.isdir(os.path.join(REC_DIR, d))]

            real_sources = await run_in_executor(list_real_sources)

            for src in real_sources:
                path = os.path.join(REC_DIR, src)
                files = await scan_source_async(src, path)
                if files:
                    grouped_recordings[src] = files

            return grouped_recordings

        except Exception as e:
            logger.error(f"Recorder History Error: {e}")
            return {}

    @staticmethod
    @alru_cache(ttl=60)
    async def get_creation_rate(minutes: int = 60) -> float:
        """Calculate files created per minute over the last X minutes."""
        try:
            now = time.time()
            cutoff = now - (minutes * 60)

            if not os.path.exists(REC_DIR):
                return 0.0

            # Scan directory (non-recursive for now, assuming flat structure or dated folders?)
            # Recorder uses dated folders typically?
            # Actually pattern is "%Y-%m-%d_%H-%M-%S.flac" inside BASE_OUTPUT_DIR/profile_slug
            # But REC_DIR should point to the active profile dir?
            # Dashboard Config: AUDIO_DIR = "/data/recording"
            # We might need to scan subdirs if profile is used.
            # Let's assume recursion for robustness or check depth 1.

            # Return rate per minute
            def count_recent() -> int:
                count = 0
                for root, _dirs, files in os.walk(REC_DIR):
                    for f in files:
                        if not f.endswith(".flac"):
                            continue

                        ts_str = f.split(".")[0]
                        try:
                            dt = datetime.datetime.strptime(ts_str, "%Y-%m-%d_%H-%M-%S")
                            ts = dt.replace(tzinfo=UTC).timestamp()
                            if ts >= cutoff:
                                count += 1
                        except Exception:
                            # Fallback
                            try:
                                mtime = os.path.getmtime(os.path.join(root, f))
                                if mtime >= cutoff:
                                    count += 1
                            except Exception:
                                pass
                return count

            total = await run_in_executor(count_recent)
            return round(total / minutes, 2)

        except Exception as e:
            logger.error(f"Recorder Rate Error: {e}")
            return 0.0

    @staticmethod
    async def get_latest_filename() -> str | None:
        """Get the filename of the most recent recording on disk."""
        try:
            if not os.path.exists(REC_DIR):
                return None

            def scan_latest() -> str | None:
                all_files = []
                for _root, _dirs, files in os.walk(REC_DIR):
                    for f in files:
                        if f.endswith(".flac"):
                            all_files.append(f)
                if not all_files:
                    return None
                return max(all_files)

            return await run_in_executor(scan_latest)
        except Exception:
            return None

    @staticmethod
    @alru_cache(ttl=30)
    async def count_files_after(filename: str | None) -> int:
        """Count how many files on disk are lexicographically 'after' the given filename."""
        if not filename:
            # If no comparison file provided, count ALL files (queue is full)
            # But this might be huge if starting fresh.
            # If processed table is empty, lag is Everything.
            # We should probably count all.
            pass

        try:
            if not os.path.exists(REC_DIR):
                return 0

            def count_walk() -> int:
                c = 0
                for _root, _dirs, files in os.walk(REC_DIR):
                    for f in files:
                        if f.endswith(".flac"):
                            if not filename or f > filename:
                                c += 1
                return c

            return await run_in_executor(count_walk)
        except Exception as e:
            logger.error(f"Recorder Count After Error: {e}")
            return 0
